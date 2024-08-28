from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse, urljoin
import requests
import csv
import re
import os

def obtener_palabras_clave_existentes(archivo):
    palabras_clave_existentes = set()
    if os.path.exists(archivo):
        with open(archivo, "r", newline="", encoding="utf-8") as archivo_csv_lectura:
            lector = csv.DictReader(archivo_csv_lectura)
            for fila in lector:
                palabras_clave_existentes.add(fila["Titulo"])
    return palabras_clave_existentes

def limpiar_texto(texto):
    texto = texto.replace("\n", " ")
    texto = texto.replace("\"", "'")
    texto = texto.replace("*", "")
    texto = texto.replace("[", "")
    texto = texto.replace("]", "")
    texto = re.sub(r"\s+", " ", texto)
    return texto

url_index = 0
urls = ["http://localhost:8888/v1/generation/text-to-image", "http://localhost:8889/v1/generation/text-to-image"]

def crear_imagen(titulo, slug):
    global url_index
    alt = limpiar_texto(argostranslate.translate.translate(titulo, "es", "en")).replace("-", " ")
    print(alt)
    nombre = f"{slug.replace('-', '_')}_{os.urandom(2).hex()}.webp"
    url = urls[url_index]
    url_index = (url_index + 1) % len(urls)
    headers = {"Content-Type": "application/json"}
    data = {
        "prompt": f"{alt}, hd detailed, detailed drawing, maximum quality, cinematic atmosphere, 8k, uhd, masterpiece",
        "negative_prompt": "sexualize, objectify, naked, nude, cgi, photo, text, caption, low quality, lowest quality, watermark, several legs, severed arms, more than two arms, anime",
        "aspect_ratios_selection": "1280*768",
        "performance_selection": "Extreme Speed"
    }
    response = requests.post(url, headers=headers, json=data)
    response_json = response.json()
    url_devuelta = response_json[0]['url']
    parsed_original_url = urlparse(url)
    parsed_returned_url = urlparse(url_devuelta)
    if parsed_original_url.port != parsed_returned_url.port:
        url_devuelta = urljoin(f"http://{parsed_returned_url.hostname}:{parsed_original_url.port}", parsed_returned_url.path)
    response_image = requests.get(url_devuelta)
    with open(f"0. Imagenes/{nombre}.webp", "wb") as archivo:
        archivo.write(response_image.content)
    return nombre, titulo

def llamada_crear_imagen(args):
    pos_end, pos_start, subtitulo, titulo, slug = args
    imagen, alt = crear_imagen(f"{subtitulo} de {titulo}", slug)
    return imagen, alt, pos_end, pos_start

def agregar_imagenes(titulo, slug):
    portada = ""
    alt_portada = ""
    try:
        portada, alt_portada = crear_imagen(titulo, slug)
    except Exception as e:
        print(f"Error generando resultado de la imagen de portada: {e}")
        portada, alt_portada = "", ""
    return portada, alt_portada

archivo_destino = "1. Redactado IMGs.csv"
palabras_clave_existentes = obtener_palabras_clave_existentes(archivo_destino)
contador_registros = 0

def procesar_fila(fila):
    global contador_registros
    contador_registros += 1
    titulo = fila["Titulo"]
    slug = fila["Slug"]
    print(f"\n\nProgreso: {contador_registros} | Título: {titulo}")
    portada, alt_portada = agregar_imagenes(titulo, slug)
    fila["Portada"] = portada
    fila["Alt"] = alt_portada
    return fila

with open("0. Redactado.csv", "r", newline="", encoding="utf-8") as archivo_csv_lectura, \
     open(archivo_destino, "a", newline="", encoding="utf-8") as archivo_csv_escritura:
    lector = csv.DictReader(archivo_csv_lectura)
    nombres_columnas = lector.fieldnames + ['Alt', 'Portada']
    escritor = csv.DictWriter(archivo_csv_escritura, fieldnames=nombres_columnas)
    if os.stat(archivo_destino).st_size == 0:
        escritor.writeheader()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = []
        for fila in lector:
            if fila["Titulo"] not in palabras_clave_existentes:
                futures.append(executor.submit(procesar_fila, fila))
        
        for future in futures:
            fila_procesada = future.result()
            escritor.writerow(fila_procesada)