import psycopg2
import psycopg2.extras
import datetime
from config import Config

def get_db_connection():
    conn = psycopg2.connect(Config.DATABASE)
    return conn

def add_or_update_tema(medio_id, nombre, url, primera_vez=None, ultima_vez=None):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Verificar si el tema ya existe
    cursor.execute(
        "SELECT id, primera_vez FROM temas WHERE medio_id = %s AND nombre = %s AND url = %s",
        (medio_id, nombre, url)
    )
    tema_existente = cursor.fetchone()
    
    now = ultima_vez or datetime.datetime.now()

    if tema_existente:
        # Actualizar tema existente
        cursor.execute(
            "UPDATE temas SET ultima_vez = %s WHERE id = %s",
            (now, tema_existente['id'])
        )
    else:
        primera_vez = primera_vez or now
        cursor.execute(
            "INSERT INTO temas (medio_id, nombre, url, primera_vez, ultima_vez) VALUES (%s, %s, %s, %s, %s)",
            (medio_id, nombre, url, primera_vez, now)
        )
    
    conn.commit()
    conn.close()

def get_temas(tipo_medio='todos', medio_id=None, limit=100, offset=0):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    query = """
    SELECT t.id, t.nombre, t.url, t.primera_vez, t.ultima_vez, 
           m.nombre as medio_nombre, m.url as medio_url, m.tipo as medio_tipo, m.id as medio_id
    FROM temas t
    JOIN medios m ON t.medio_id = m.id
    """
    
    condiciones = []
    params = []

    if tipo_medio != 'todos':
        condiciones.append("m.tipo = %s")
        params.append(tipo_medio)
    
    if medio_id:
        condiciones.append("m.id = %s")
        params.append(medio_id)

    if condiciones:
        query += " WHERE " + " AND ".join(condiciones)

    query += " ORDER BY t.ultima_vez DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    temas = []
    for row in rows:
        primera_vez = row['primera_vez']
        ultima_vez = row['ultima_vez']
        ahora = datetime.datetime.now()
        
        duracion_horas = (ahora - primera_vez).total_seconds() / 3600
        
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
            'id': row['id'],
            'nombre': row['nombre'],
            'url': row['url'],
            'primera_vez': primera_vez.strftime('%Y-%m-%d %H:%M:%S'),
            'ultima_vez': ultima_vez.strftime('%Y-%m-%d %H:%M:%S'),
            'medio_nombre': row['medio_nombre'],
            'medio_url': row['medio_url'],
            'medio_tipo': row['medio_tipo'],
            'medio_id': row['medio_id'],
            'duracion_horas': round(duracion_horas, 1),
            'estado': estado,
            'color': color
        })
    
    conn.close()
    return temas

def get_tema_stats():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    cursor.execute("SELECT COUNT(*) as total FROM temas")
    total_temas = cursor.fetchone()['total']
    
    conn.close()
    return {'total': total_temas}

import urllib.parse

def get_temas_por_dominio(dominio):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    dominio = dominio.lower().replace("www.", "")
    print(f"[API] Filtrando temas por dominio: {dominio}")

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
        medio_url = row['medio_url']
        hostname = urllib.parse.urlparse(medio_url).hostname or ""
        hostname = hostname.replace("www.", "").lower()

        if dominio not in hostname:
            continue  # Saltar si no coincide

        primera_vez = row['primera_vez']
        duracion_horas = (ahora - primera_vez).total_seconds() / 3600

        # Determinar color y estado
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

def get_temas(tipo_medio='todos', medio_id=None, limit=100, offset=0):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    query = """
    SELECT t.id, t.nombre, t.url, t.primera_vez, t.ultima_vez, 
           m.nombre as medio_nombre, m.url as medio_url, m.tipo as medio_tipo, m.id as medio_id
    FROM temas t
    JOIN medios m ON t.medio_id = m.id
    """

    condiciones = []
    params = []

    if tipo_medio != 'todos':
        condiciones.append("m.tipo = %s")
        params.append(tipo_medio)

    if medio_id:
        condiciones.append("m.id = %s")
        params.append(medio_id)

    if condiciones:
        query += " WHERE " + " AND ".join(condiciones)

    query += " ORDER BY t.ultima_vez DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    ahora = datetime.datetime.now()
    temas = []
    for row in rows:
        primera_vez = row['primera_vez']
        ultima_vez = row['ultima_vez']

        duracion_horas = (ahora - primera_vez).total_seconds() / 3600

        if duracion_horas < 4:
            color = "#4caf50"
        elif duracion_horas < 24:
            color = "#ffc107"
        else:
            color = "#f44336"

        temas.append({
            'id': row['id'],
            'nombre': row['nombre'],
            'url': row['url'],
            'primera_vez': primera_vez.strftime('%Y-%m-%d %H:%M:%S'),
            'ultima_vez': ultima_vez.strftime('%Y-%m-%d %H:%M:%S'),
            'medio_nombre': row['medio_nombre'],
            'medio_url': row['medio_url'],
            'medio_tipo': row['medio_tipo'],
            'medio_id': row['medio_id'],
            'duracion_horas': round(duracion_horas, 1),
            'color': color
        })

    return temas

