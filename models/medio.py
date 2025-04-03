import psycopg2
import psycopg2.extras
from config import Config

def get_db_connection():
    conn = psycopg2.connect(Config.DATABASE)
    return conn

def get_all_medios():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT id, nombre, url, tipo FROM medios")
    medios = cursor.fetchall()  # Ya son diccionarios
    conn.close()
    return medios

def add_medio(nombre, url, tipo):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO medios (nombre, url, tipo) VALUES (%s, %s, %s)",
            (nombre, url, tipo)
        )
        conn.commit()
        conn.close()
        return {"mensaje": "Medio agregado correctamente"}, 201
    except psycopg2.IntegrityError:
        conn.rollback()
        conn.close()
        return {"mensaje": "El medio ya existe"}, 409
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return {"mensaje": f"Error inesperado: {str(e)}"}, 500


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
