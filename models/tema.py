import psycopg2
import psycopg2.extras
import datetime
import urllib.parse
from config import Config
from bs4 import BeautifulSoup

SELECTORES_POR_DOMINIO = {
    "sport.es": ".news",
    "epe.es": ".ft-org-header-sidenav-body-header-nav",
    "elperiodico.com": ".ft-org-header-nav__list",
}

def extraer_temas_visibles(html, url):
    from bs4 import BeautifulSoup
    import urllib.parse
    import logging

    try:
        parsed = urllib.parse.urlparse(url)
        hostname = parsed.hostname or ""
    except Exception as e:
        import logging
        logging.error(f"[Extractor] Error al parsear URL: {url} → {e}")
        return []

    dominio = hostname.replace("www.", "").lower()



    selector = None
    for clave in SELECTORES_POR_DOMINIO:
        if clave in dominio:
            selector = SELECTORES_POR_DOMINIO[clave]
            break

    logging.info(f"[Extractor] Dominio base detectado: {dominio} → usando selector: {selector}")

    temas = []
    soup = BeautifulSoup(html, "html.parser")

    if selector:
        contenedor = soup.select_one(selector)
        if contenedor:
            enlaces = contenedor.find_all("a")
            for i, link in enumerate(enlaces):
                texto = link.get_text(strip=True)
                href = link.get("href")

                if "elperiodico.com" in dominio and i == 0:
                    continue  # Ignorar "Es noticia"

                if texto and href and len(texto) < 50:
                    temas.append({
                        "nombre": texto,
                        "url": href if href.startswith("http") else f"https://{hostname}{href}"
                    })
    return temas




def get_db_connection():
    conn = psycopg2.connect(Config.DATABASE)
    return conn

def add_or_update_tema(medio_id, nombre, url, primera_vez=None, ultima_vez=None):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute(
        "SELECT id, primera_vez FROM temas WHERE medio_id = %s AND nombre = %s AND url = %s",
        (medio_id, nombre, url)
    )
    tema_existente = cursor.fetchone()
    now = ultima_vez or datetime.datetime.now()

    if tema_existente:
        cursor.execute("UPDATE temas SET ultima_vez = %s WHERE id = %s", (now, tema_existente['id']))
    else:
        primera_vez = primera_vez or now
        cursor.execute(
            "INSERT INTO temas (medio_id, nombre, url, primera_vez, ultima_vez) VALUES (%s, %s, %s, %s, %s)",
            (medio_id, nombre, url, primera_vez, now)
        )

    conn.commit()
    conn.close()

def get_temas_visualizacion(medio_id=None, tipo_medio='', page=1, per_page=20):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    offset = (page - 1) * per_page
    condiciones = []
    params = []

    if tipo_medio:
        condiciones.append("m.tipo = %s")
        params.append(tipo_medio)
    if medio_id:
        condiciones.append("m.id = %s")
        params.append(medio_id)

    where_clause = " WHERE " + " AND ".join(condiciones) if condiciones else ""

    query = f"""
    SELECT t.id, t.nombre, t.url, t.primera_vez, t.ultima_vez,
           m.nombre as medio_nombre, m.url as medio_url, m.tipo as medio_tipo, m.id as medio_id
    FROM temas t
    JOIN medios m ON t.medio_id = m.id
    {where_clause}
    ORDER BY t.ultima_vez DESC
    LIMIT %s OFFSET %s
    """

    params.extend([per_page, offset])
    cursor.execute(query, params)
    rows = cursor.fetchall()

    temas = []
    ahora = datetime.datetime.now()
    for row in rows:
        duracion_horas = (ahora - row['primera_vez']).total_seconds() / 3600
        if duracion_horas < 4:
            estado = "verde"
        elif duracion_horas < 24:
            estado = "amarillo"
        else:
            estado = "rojo"

        temas.append({
            'id': row['id'],
            'nombre': row['nombre'],
            'url': row['url'],
            'primera_vez': row['primera_vez'].strftime('%Y-%m-%d %H:%M:%S'),
            'ultima_vez': row['ultima_vez'].strftime('%Y-%m-%d %H:%M:%S'),
            'medio_nombre': row['medio_nombre'],
            'medio_url': row['medio_url'],
            'medio_tipo': row['medio_tipo'],
            'medio_id': row['medio_id'],
            'duracion_horas': round(duracion_horas, 1),
            'estado': estado
        })

    cursor.execute("SELECT id, nombre, tipo FROM medios ORDER BY nombre")
    medios = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) as total FROM temas")
    total_temas = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) FILTER (WHERE tipo = 'propio') as propios, COUNT(*) FILTER (WHERE tipo = 'competencia') as competencia, COUNT(*) as total FROM medios")
    medios_stats = cursor.fetchone()

    conn.close()

    return temas, medios, {"temas": {"total": total_temas}, "medios": medios_stats}

def get_temas_por_dominio(dominio):
    import re

    def normalizar_dominio(d):
        if not d:
            return ""
        d = d.lower()
        d = d.replace("https://", "").replace("http://", "").replace("www.", "")
        d = re.sub(r"/.*", "", d)  # Eliminar cualquier ruta (/es/, /noticias/, etc.)
        return d.strip()

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    dominio_limpio = normalizar_dominio(dominio)

    query = """
    SELECT t.id, t.nombre, t.url, t.primera_vez, t.ultima_vez,
           m.nombre as medio_nombre, m.url as medio_url, m.tipo as medio_tipo, m.id as medio_id
    FROM temas t
    JOIN medios m ON t.medio_id = m.id
    ORDER BY t.ultima_vez DESC
    """

    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()

    ahora = datetime.datetime.now()
    temas = []

    for row in rows:
        medio_url = row['medio_url'] or ""
        medio_limpio = normalizar_dominio(medio_url)

        if dominio_limpio != medio_limpio:
            continue

        duracion_horas = (ahora - row['primera_vez']).total_seconds() / 3600
        if duracion_horas < 4:
            estado = "verde"
            color = "#4caf50"
        elif duracion_horas < 24:
            estado = "amarillo"
            color = "#ffc107"
        else:
            estado = "rojo"
            color = "#f44336"

        temas.append({
            "text": row['nombre'],
            "href": row['url'],
            "color": color,
            "estado": estado,
            "duracion_horas": round(duracion_horas, 1)
        })

    return temas

