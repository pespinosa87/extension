import psycopg2
import psycopg2.extras
from config import Config

def get_db_connection():
    conn = psycopg2.connect(Config.DATABASE)
    return conn


def get_all_medios():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, url, tipo FROM medios")
    medios = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return medios

def add_medio(nombre, url, tipo):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
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
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
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