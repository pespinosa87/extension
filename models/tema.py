import sqlite3
import datetime
from config import Config

def get_db_connection():
    conn = sqlite3.connect(Config.DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def add_or_update_tema(medio_id, nombre, url, primera_vez=None, ultima_vez=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verificar si el tema ya existe
    cursor.execute(
        "SELECT id, primera_vez FROM temas WHERE medio_id = ? AND nombre = ? AND url = ?",
        (medio_id, nombre, url)
    )
    tema_existente = cursor.fetchone()
    
    now = ultima_vez or datetime.datetime.now().isoformat()
    
    if tema_existente:
        # Actualizar tema existente
        cursor.execute(
            "UPDATE temas SET ultima_vez = ? WHERE id = ?",
            (now, tema_existente['id'])
        )
    else:
        # Nuevo tema
        primera_vez = primera_vez or now
        cursor.execute(
            "INSERT INTO temas (medio_id, nombre, url, primera_vez, ultima_vez) VALUES (?, ?, ?, ?, ?)",
            (medio_id, nombre, url, primera_vez, now)
        )
    
    conn.commit()
    conn.close()

def get_temas(tipo_medio='todos', limit=100):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
    SELECT t.id, t.nombre, t.url, t.primera_vez, t.ultima_vez, 
           m.nombre as medio_nombre, m.url as medio_url, m.tipo as medio_tipo, m.id as medio_id
    FROM temas t
    JOIN medios m ON t.medio_id = m.id
    """
    
    params = ()
    if tipo_medio != 'todos':
        query += " WHERE m.tipo = ?"
        params = (tipo_medio,)
    
    query += " ORDER BY t.ultima_vez DESC LIMIT ?"
    params = params + (limit,)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    temas = []
    for row in rows:
        primera_vez = datetime.datetime.fromisoformat(row['primera_vez'])
        ultima_vez = datetime.datetime.fromisoformat(row['ultima_vez'])
        ahora = datetime.datetime.now()
        
        # Calcular duración en horas
        duracion_horas = (ahora - primera_vez).total_seconds() / 3600
        
        # Determinar estado según duración
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
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as total FROM temas")
    total_temas = cursor.fetchone()['total']
    
    conn.close()
    return {'total': total_temas}