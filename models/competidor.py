import psycopg2
import psycopg2.extras
from config import Config

def get_db_connection():
    return psycopg2.connect(Config.DATABASE)

def add_competidor(medio_competidor_id, medio_padre_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO competidores (medio_competidor_id, medio_padre_id)
        VALUES (%s, %s)
        ON CONFLICT DO NOTHING
    """, (medio_competidor_id, medio_padre_id))
    conn.commit()
    conn.close()

def get_competidores_por_medio_padre(medio_padre_id):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("""
        SELECT m.* FROM competidores c
        JOIN medios m ON c.medio_competidor_id = m.id
        WHERE c.medio_padre_id = %s
    """, (medio_padre_id,))
    resultados = cursor.fetchall()
    conn.close()
    return resultados