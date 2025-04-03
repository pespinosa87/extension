import psycopg2
import psycopg2.extras
import datetime
import urllib.parse
from config import Config

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
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    dominio = dominio.lower().replace("www.", "")
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
        hostname = urllib.parse.urlparse(row['medio_url']).hostname or ""
        if dominio not in hostname.replace("www.", "").lower():
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