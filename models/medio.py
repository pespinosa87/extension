import sqlite3
from config import Config

def get_db_connection():
    conn = sqlite3.connect(Config.DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS medios (
        id INTEGER PRIMARY KEY,
        nombre TEXT UNIQUE,
        url TEXT,
        tipo TEXT  -- 'propio' o 'competencia'
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS temas (
        id INTEGER PRIMARY KEY,
        medio_id INTEGER,
        nombre TEXT,
        url TEXT,
        primera_vez TIMESTAMP,
        ultima_vez TIMESTAMP,
        FOREIGN KEY (medio_id) REFERENCES medios (id)
    )
    ''')
    conn.commit()
    conn.close()

def get_all_medios():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, url, tipo FROM medios")
    medios = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return medios

def add_medio(nombre, url, tipo):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO medios (nombre, url, tipo) VALUES (?, ?, ?)",
            (nombre, url, tipo)
        )
        conn.commit()
        medio_id = cursor.lastrowid
        conn.close()
        return {'id': medio_id, 'mensaje': 'Medio agregado correctamente'}, 201
    except sqlite3.IntegrityError:
        conn.close()
        return {'error': 'El medio ya existe'}, 409

def get_medio_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as total FROM medios")
    total_medios = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as total FROM medios WHERE tipo = 'propio'")
    medios_propios = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as total FROM medios WHERE tipo = 'competencia'")
    medios_competencia = cursor.fetchone()['total']
    
    conn.close()
    
    return {
        'total': total_medios,
        'propios': medios_propios,
        'competencia': medios_competencia
    }