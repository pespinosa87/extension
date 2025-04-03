import requests
from bs4 import BeautifulSoup
import datetime
import pytz
import time
import logging
from apscheduler.schedulers.background import BackgroundScheduler

from models.medio import get_all_medios, add_medio
from models.tema import add_or_update_tema, get_db_connection

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
    """
    Elimina temas más antiguos, manteniendo 7 días completos de histórico
    
    Args:
        dias_historico (int): Número de días de histórico a mantener
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Calcular fecha límite (7 días completos de histórico)
        fecha_limite = datetime.datetime.now() - datetime.timedelta(days=dias_historico)
        
        # Eliminar temas más antiguos que la fecha límite
        cursor.execute(
            "DELETE FROM temas WHERE ultima_vez < ?", 
            (fecha_limite.isoformat(),)
        )
        
        conn.commit()
        rows_deleted = cursor.rowcount
        logger.info(f"Limpieza de temas: Eliminados {rows_deleted} temas anteriores a {fecha_limite}")
        
        conn.close()
    except Exception as e:
        logger.error(f"Error al limpiar temas antiguos: {e}")

def obtener_temas_de_web(medio_id, url, tipo_medio, selector_temas=None, timeout=15):
    """
    Extrae los temas y URLs del sitio web utilizando el selector CSS específico.
    """
    try:
        # Configurar headers para simular un navegador real
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        logger.info(f"Obteniendo contenido de {url}...")
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        # Si no se proporciona selector, obtener el selector predeterminado
        if not selector_temas:
            if tipo_medio == 'propio':
                # Selectores para diferentes tipos de medios
                selectors_propios = [
                    ".ft-org-header-regionales-menu-panel__tagbar a",
                    ".tags a",
                    ".tag-list a",
                    "a.tag"
                ]
                
                # Probar múltiples selectores
                for selector in selectors_propios:
                    temas_elementos = BeautifulSoup(response.text, 'html.parser').select(selector)
                    if temas_elementos:
                        selector_temas = selector
                        break
            else:
                # Para competencia, selectores genéricos
                selector_temas = "a.tag, a.tema, .tags a, .tag-list a"
        
        logger.info(f"Usando selector: {selector_temas}")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extraer temas
        temas_elementos = soup.select(selector_temas)
        logger.info(f"Encontrados {len(temas_elementos)} elementos con el selector")
        
        temas = []
        for elemento in temas_elementos:
            nombre = elemento.text.strip()
            url_tema = elemento.get('href', '')
            
            # Si la URL es relativa, convertirla a absoluta
            if url_tema and not url_tema.startswith(('http://', 'https://')):
                base_url = '/'.join(url.split('/')[:3])  # Extraer dominio
                url_tema = f"{base_url}{url_tema if url_tema.startswith('/') else '/' + url_tema}"
            
            if nombre and url_tema:  # Solo agregar si tiene nombre y URL
                temas.append((nombre, url_tema))
                logger.info(f"Tema encontrado: {nombre} -> {url_tema}")
        
        return temas
    
    except Exception as e:
        logger.error(f"Error al obtener temas de {url}: {str(e)}")
        return []

def escanear_medios_por_lotes(lote_size=5):
    """Función para escanear medios en lotes"""
    logger.info(f"Iniciando escaneo a las {datetime.datetime.now()}")
    
    medios = get_all_medios()
    
    total_medios = len(medios)
    medios_procesados = 0
    temas_encontrados = 0
    
    for i in range(0, total_medios, lote_size):
        lote_actual = medios[i:i+lote_size]
        
        for medio in lote_actual:
            print(f"[{medios_procesados+1}/{total_medios}] Escaneando medio: {medio['nombre']} ({medio['url']}) - Tipo: {medio['tipo']}")
            
            # Obtener temas
            temas = obtener_temas_de_web(medio['id'], medio['url'], medio['tipo'])
            
            if temas:
                # Actualizar temas en la base de datos
                for nombre, url in temas:
                    add_or_update_tema(medio['id'], nombre, url)
                
                temas_encontrados += len(temas)
                print(f"✓ Encontrados {len(temas)} temas en {medio['nombre']}")
            else:
                print(f"✗ No se encontraron temas en {medio['nombre']}")
            
            medios_procesados += 1
        
        # Pequeña pausa entre lotes para no sobrecargar recursos
        time.sleep(2)
    
    print(f"Escaneo completado a las {datetime.datetime.now()}")
    print(f"Resumen: {medios_procesados} medios procesados, {temas_encontrados} temas encontrados en total")
    
    return {
        "medios_procesados": medios_procesados,
        "temas_encontrados": temas_encontrados
    }

def agregar_medios_prensa():
    """Función para agregar los medios de prensa proporcionados"""
    # Lista completa de medios propios
    medios_propios = [
        {"nombre": "ABC", "url": "https://www.abc.es/", "tipo": "propio"},
        {"nombre": "20 Minutos", "url": "https://www.20minutos.es/", "tipo": "propio"},
        {"nombre": "La Vanguardia", "url": "https://www.lavanguardia.com/", "tipo": "propio"},
        {"nombre": "El País", "url": "https://elpais.com/", "tipo": "propio"},
        {"nombre": "El Mundo", "url": "https://www.elmundo.es/", "tipo": "propio"},
        {"nombre": "La Razón", "url": "https://www.larazon.es/", "tipo": "propio"},
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
        {"nombre": "EPE", "url": "https://www.epe.es/es/", "tipo": "propio"},
        {"nombre": "El Periódico", "url": "https://www.elperiodico.com/es/", "tipo": "propio"},
        {"nombre": "Sport", "url": "https://www.sport.es/es/", "tipo": "propio"}
    ]
    
    medios_agregados = 0
    medios_existentes = 0
    
    for medio in medios_propios:
        resultado, status_code = add_medio(medio["nombre"], medio["url"], medio["tipo"])
        if status_code == 201:
            medios_agregados += 1
        else:
            medios_existentes += 1
    
    logger.info(f"Agregados {medios_agregados} medios nuevos, {medios_existentes} ya existentes")
    
    return {
        "mensaje": f"Proceso completado. Medios agregados: {medios_agregados}, ya existentes: {medios_existentes}",
    }

def init_scheduler():
    """Inicializar el programador de tareas"""
    # Configurar el programador con zona horaria UTC
    scheduler = BackgroundScheduler(timezone=pytz.UTC)
    
    # Escanear todos los medios cada hora
    scheduler.add_job(
        escanear_medios_por_lotes, 
        'interval', 
        hours=1, 
        id='escaneo_medios'
    )
    
    # Limpiar temas antiguos cada 7 días, manteniendo 7 días de histórico
    scheduler.add_job(
        limpiar_temas_antiguos, 
        'interval', 
        days=7, 
        id='limpiar_temas'
    )
    
    logger.info("Scheduler inicializado correctamente")
    return scheduler