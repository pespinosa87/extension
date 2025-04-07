import requests
from bs4 import BeautifulSoup
import datetime
import time
import pytz
import logging
import psycopg2
import psycopg2.extras
from apscheduler.schedulers.background import BackgroundScheduler

from models.tema import add_or_update_tema, get_db_connection, resetear_visibilidad_por_medio
from models.medio import get_all_medios, add_medio
from models.competidor import get_competidores_por_medio_padre

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scanner.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def limpiar_temas_antiguos(dias_historico=7):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        fecha_limite = datetime.datetime.now() - datetime.timedelta(days=dias_historico)
        cursor.execute("DELETE FROM temas WHERE ultima_vez < %s", (fecha_limite,))
        conn.commit()
        logger.info(f"Limpieza de temas: Eliminados {cursor.rowcount} temas anteriores a {fecha_limite}")
        conn.close()
    except Exception as e:
        logger.error(f"Error al limpiar temas antiguos: {e}")

TEMAS_INVALIDOS = {"es noticia", "últimas noticias", "todas las noticias", "más leídas", "tendencias"}

def obtener_temas_de_web(medio_id, url, tipo_medio, selector_temas=None, timeout=15):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        logger.info(f"Obteniendo contenido de {url}...")
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()

        if not selector_temas:
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("SELECT selector FROM medios WHERE id = %s", (medio_id,))
            medio = cursor.fetchone()
            conn.close()
            if medio and medio["selector"]:
                selector_temas = medio["selector"]

        if not selector_temas:
            if tipo_medio == 'propio':
                selectors_propios = [
                    ".ft-org-header-regionales-menu-panel__tagbar a",
                    ".tags a",
                    ".tag-list a",
                    "a.tag"
                ]
                for selector in selectors_propios:
                    elementos = BeautifulSoup(response.text, 'html.parser').select(selector)
                    if elementos:
                        selector_temas = selector
                        break
            else:
                selector_temas = "a.tag, a.tema, .tags a, .tag-list a"

        logger.info(f"Usando selector: {selector_temas}")
        soup = BeautifulSoup(response.text, 'html.parser')
        contenedor = soup.select_one(selector_temas)
        temas_elementos = contenedor.find_all("a") if contenedor else []

        logger.info(f"Encontrados {len(temas_elementos)} elementos con el selector")
        temas = []
        base_url = '/'.join(url.split('/')[:3])

        for elemento in temas_elementos:
            nombre = elemento.text.strip()
            if not nombre or nombre.lower() in TEMAS_INVALIDOS:
                continue
            url_tema = elemento.get('href')
            if not url_tema:
                continue
            if not url_tema.startswith(('http://', 'https://')):
                url_tema = f"{base_url}{url_tema if url_tema.startswith('/') else '/' + url_tema}"
            temas.append((nombre, url_tema))
            logger.info(f"Tema encontrado: {nombre} -> {url_tema}")

        return temas

    except Exception as e:
        logger.error(f"Error al obtener temas de {url}: {str(e)}")
        return []

def escanear_medios_por_lotes(lote_size=5):
    logger.info(f"Iniciando escaneo a las {datetime.datetime.now()}")
    medios = get_all_medios()
    total_medios = len(medios)
    medios_procesados = 0
    temas_encontrados = 0

    for i in range(0, total_medios, lote_size):
        lote_actual = medios[i:i+lote_size]
        for medio in lote_actual:
            print(f"[{medios_procesados+1}/{total_medios}] Escaneando medio: {medio['nombre']} ({medio['url']}) - Tipo: {medio['tipo']}")
            resetear_visibilidad_por_medio(medio['id'])
            temas = obtener_temas_de_web(medio['id'], medio['url'], medio['tipo'])
            if temas:
                for nombre, url in temas:
                    add_or_update_tema(medio['id'], nombre, url)
                temas_encontrados += len(temas)
                print(f"✓ Encontrados {len(temas)} temas en {medio['nombre']}")
            else:
                print(f"✗ No se encontraron temas en {medio['nombre']}")
            medios_procesados += 1
            time.sleep(1.5)
        time.sleep(2)

    logger.info(f"Escaneo completado. Medios: {medios_procesados}, Temas: {temas_encontrados}")
    return {"medios_procesados": medios_procesados, "temas_encontrados": temas_encontrados}

def escanear_competidores_por_lotes():
    propios = [m for m in get_all_medios() if m['tipo'] == 'propio']
    total = 0
    for medio in propios:
        competidores = get_competidores_por_medio_padre(medio['id'])
        for c in competidores:
            resetear_visibilidad_por_medio(c['id'])
            temas = obtener_temas_de_web(c['id'], c['url'], c['tipo'])
            for nombre, url in temas:
                add_or_update_tema(c['id'], nombre, url)
                total += 1
    logger.info(f"Escaneo de competidores completado. Temas encontrados: {total}")
    return {"temas_encontrados": total}

def agregar_medios_prensa():
    medios_propios = [
        {"nombre": "Diari de Girona", "url": "https://www.diaridegirona.cat/", "tipo": "propio"},
        {"nombre": "Diario Córdoba", "url": "https://www.diariocordoba.com/", "tipo": "propio"},
        {"nombre": "Diario de Ibiza", "url": "https://www.diariodeibiza.es/", "tipo": "propio"},
        {"nombre": "Información", "url": "https://www.informacion.es/", "tipo": "propio"},
        {"nombre": "Diario de Mallorca", "url": "https://www.diariodemallorca.es/", "tipo": "propio"},
        {"nombre": "El Día", "url": "https://www.eldia.es/", "tipo": "propio"},
        {"nombre": "Empordà", "url": "https://www.emporda.info/", "tipo": "propio"},
        {"nombre": "El Periódico de Aragón", "url": "https://www.elperiodicodearagon.com/", "tipo": "propio"},
        {"nombre": "El Periódico Extremadura", "url": "https://www.elperiodicoextremadura.com/", "tipo": "propio"},
        {"nombre": "El Periódico Mediterráneo", "url": "https://www.elperiodicomediterraneo.com/", "tipo": "propio"},
        {"nombre": "Faro de Vigo", "url": "https://www.farodevigo.es/", "tipo": "propio"},
        {"nombre": "La Crónica de Badajoz", "url": "https://www.lacronicabadajoz.com/", "tipo": "propio"},
        {"nombre": "La Nueva España", "url": "https://www.lne.es/", "tipo": "propio"},
        {"nombre": "La Opinión A Coruña", "url": "https://www.laopinioncoruna.es/", "tipo": "propio"},
        {"nombre": "La Opinión de Murcia", "url": "https://www.laopiniondemurcia.es/", "tipo": "propio"},
        {"nombre": "La Opinión de Málaga", "url": "https://www.laopiniondemalaga.es/", "tipo": "propio"},
        {"nombre": "La Opinión de Zamora", "url": "https://www.laopiniondezamora.es/", "tipo": "propio"},
        {"nombre": "La Provincia", "url": "https://www.laprovincia.es/", "tipo": "propio"},
        {"nombre": "Levante-EMV", "url": "https://www.levante-emv.com/", "tipo": "propio"},
        {"nombre": "Mallorca Zeitung", "url": "https://www.mallorcazeitung.es/", "tipo": "propio"},
        {"nombre": "Regió7", "url": "https://www.regio7.cat/", "tipo": "propio"},
        {"nombre": "Superdeporte", "url": "https://www.superdeporte.es/", "tipo": "propio"},
        {"nombre": "El Correo Gallego", "url": "https://www.elcorreogallego.es/", "tipo": "propio"},
        {"nombre": "El Correo Web", "url": "https://www.elcorreoweb.es/", "tipo": "propio"},
        {"nombre": "EPE", "url": "https://www.epe.es/es/", "tipo": "propio", "selector": "ul.ft-org-header-sidenav-body-header-nav"},
        {"nombre": "El Periódico", "url": "https://www.elperiodico.com/es/", "tipo": "propio", "selector": "ul.ft-org-header-nav__list"},
        {"nombre": "Sport", "url": "https://www.sport.es/es/", "tipo": "propio", "selector": "ul.itemsContainer"}
    ]

    medios_agregados = 0
    medios_existentes = 0

    for medio in medios_propios:
        resultado, status_code = add_medio(medio["nombre"], medio["url"], medio["tipo"], medio.get("selector"))
        if status_code == 201:
            medios_agregados += 1
        else:
            medios_existentes += 1

    logger.info(f"Agregados {medios_agregados} medios nuevos, {medios_existentes} ya existentes")
    return {"mensaje": f"Proceso completado. Medios agregados: {medios_agregados}, ya existentes: {medios_existentes}"}

def init_scheduler():
    scheduler = BackgroundScheduler(timezone=pytz.UTC)
    scheduler.add_job(escanear_medios_por_lotes, 'interval', hours=1, id='escaneo_medios')
    scheduler.add_job(limpiar_temas_antiguos, 'interval', days=7, id='limpiar_temas')
    logger.info("Scheduler inicializado correctamente")
    return scheduler
