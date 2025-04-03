import requests
from bs4 import BeautifulSoup
import datetime
import pytz
from apscheduler.schedulers.background import BackgroundScheduler

from models.medio import get_all_medios
from models.tema import add_or_update_tema

def obtener_temas_de_web(medio_id, url, tipo_medio, selector_temas=None):
    """
    Extrae los temas y URLs del sitio web utilizando el selector CSS específico.
    """
    try:
        # Configurar headers para simular un navegador real
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Obtener el contenido de la página
        print(f"Obteniendo contenido de {url}...")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Si no se proporciona selector, obtener el selector predeterminado
        if not selector_temas:
            if tipo_medio == 'propio':
                # Para medios propios, usar el selector específico mencionado
                selector_temas = ".ft-org-header-regionales-menu-panel__tagbar a"
            else:
                # Para competencia, usar un selector genérico
                selector_temas = "a.tag, a.tema, .tags a"
        
        print(f"Usando selector: {selector_temas}")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extraer temas
        temas_elementos = soup.select(selector_temas)
        print(f"Encontrados {len(temas_elementos)} elementos con el selector")
        
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
                print(f"Tema encontrado: {nombre} -> {url_tema}")
        
        return temas
    
    except Exception as e:
        print(f"Error al obtener temas de {url}: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def escanear_todos_los_medios():
    """Función para escanear todos los medios registrados"""
    print(f"Iniciando escaneo a las {datetime.datetime.now()}")
    
    medios = get_all_medios()
    
    total_medios = len(medios)
    medios_procesados = 0
    temas_encontrados = 0
    
    for medio in medios:
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
    
    print(f"Escaneo completado a las {datetime.datetime.now()}")
    print(f"Resumen: {medios_procesados} medios procesados, {temas_encontrados} temas encontrados en total")
    
    return {
        "medios_procesados": medios_procesados,
        "temas_encontrados": temas_encontrados
    }

def agregar_medios_prensa():
    """Función para agregar los medios de prensa proporcionados"""
    from models.medio import add_medio
    
    # Lista de medios propios
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
    
    # No iniciamos el escaneo automáticamente para evitar timeouts
    return {
        "mensaje": f"Proceso completado. Medios agregados: {medios_agregados}, ya existentes: {medios_existentes}",
    }

def init_scheduler():
    # Configurar el programador para escanear cada hora
    scheduler = BackgroundScheduler(timezone=pytz.UTC)
    scheduler.add_job(escanear_todos_los_medios, 'interval', hours=1)
    return scheduler