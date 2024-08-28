import time  # Importa el módulo time
from openai import OpenAI
import unicodedata
import markdown2
import json
import csv
import re
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# Registro del inicio del tiempo
inicio = time.time()

openai = OpenAI(base_url="http://localhost:11434/v1", api_key="temp")

url_index = 0
urls = ["http://localhost:11434/v1", "http://localhost:11435/v1", "http://localhost:11436/v1"]

keywords = [line.strip() for line in open("keywords.txt", "r", encoding="utf-8")]
categorias = ' '.join([line.strip() for line in open("categorias.txt", "r", encoding="utf-8").read().strip().split('\n')])

total_keywords = len(keywords)
contador_keywords = 0

titulo_prompt = json.load(open("0. Prompts/0. Titulo.json", encoding="utf-8"))
articulo_prompt = json.load(open("1. Prompts/1. Articulo.json", encoding="utf-8"))
categoria_prompt = json.load(open("2. Prompts/2. Categoria.json", encoding="utf-8"))

def reemplazar_json(prompts, reemplazos):
    prompts_copy = [prompt.copy() for prompt in prompts]
    for prompt in prompts_copy:
        for clave, valor in reemplazos.items():
            prompt['content'] = prompt['content'].replace(clave, valor)
    return prompts_copy

def chat(pjson, reemplazos):
    global url_index
    openai.base_url = urls[url_index]
    url_index = (url_index + 1) % len(urls)
    prompt = pjson.copy()
    def consultar(prompt):
        return openai.chat.completions.create(
            model="gemma2:2b",
            messages=prompt
        ).choices[0].message.content.strip()
    prompt = reemplazar_json(prompt, reemplazos)
    respuesta = consultar(prompt)
    print(".", end="")
    return respuesta

def limpiar_texto(texto):
    texto = texto.replace("\n", " ")
    texto = texto.replace("\"", "'")
    texto = texto.replace("*", "")
    texto = texto.replace("#", "")
    texto = texto.replace("-", "")
    return texto

def crear_titulo(keyword):
    titulo = chat(titulo_prompt, {'[keyword]': keyword})
    titulo = limpiar_texto(titulo)
    titulo = titulo.replace("Título: ", "")
    titulo = titulo.strip('"')
    return titulo

def crear_articulo(titulo):
    articulo = chat(articulo_prompt, {'[titulo]': titulo})
    articulo = markdown2.markdown(articulo)
    articulo = re.sub(r'En (conclusión|resumen|general)', lambda match: match.group(0).upper(), articulo)
    articulo = articulo.replace("En resumen,", "")
    articulo = articulo.replace("En conclusión,", "")
    articulo = articulo.strip()
    return articulo

def crear_categoria(titulo):
    categoria = chat(categoria_prompt, {'[titulo]': titulo, '[categorias]': categorias})
    categoria = categoria.split("\n")[0]
    categoria = limpiar_texto(categoria)
    return categoria

def crear_slug(keyword):
    palabras_clave = keyword.split(" ")
    palabra_mas_corta = min(palabras_clave, key=len).lower()
    slug = unicodedata.normalize('NFKD', palabra_mas_corta)
    slug = slug.encode('ASCII', 'ignore').decode('ASCII')
    slug = slug.replace(" ", "-")
    slug = re.sub(r'[^\w-]', '', slug)
    return slug

def leer_keywords_existentes(nombre_archivo):
    if not os.path.isfile(nombre_archivo):
        return set()
    
    with open(nombre_archivo, "r", newline="", encoding="utf-8") as archivo_csv:
        lector = csv.reader(archivo_csv)
        next(lector, None)
        keywords_set = {fila[0] for fila in lector}
    
    return keywords_set

def procesar_keyword(keyword):
    global contador_keywords
    contador_keywords += 1
    print(f"\nProgreso: {(contador_keywords/total_keywords)*100:.2f}% | Keyword: {keyword}")
    titulo = crear_titulo(keyword)
    articulo = crear_articulo(titulo)
    categoria = crear_categoria(titulo)
    slug = crear_slug(keyword)
    return [keyword, titulo, articulo, categoria, slug]

keywords_existentes = leer_keywords_existentes("2. Articulos.csv")
keywords_faltantes = [kw for kw in keywords if kw not in keywords_existentes]
total_keywords = len(keywords_faltantes)

with open("2. Articulos.csv", "a", newline="", encoding="utf-8") as archivo_csv:
    escritor = csv.writer(archivo_csv)
    if archivo_csv.tell() == 0:
        escritor.writerow(["Keyword", "Titulo", "Articulo", "Categoria", "Slug"])

    with ThreadPoolExecutor(max_workers=1) as executor:
        futuros = {executor.submit(procesar_keyword, kw): kw for kw in keywords_faltantes}
        
        for futuro in as_completed(futuros):
            resultado = futuro.result()
            escritor.writerow(resultado)

# Registro del final del tiempo
fin = time.time()

# Mostrar el tiempo de ejecución total
tiempo_total = fin - inicio
print(f"\n\nTiempo total de ejecución: {tiempo_total:.2f} segundos")