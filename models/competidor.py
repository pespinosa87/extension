import psycopg2
from config import Config

def get_competidores_relacionados(dominio_actual):
    conn = psycopg2.connect(Config.DATABASE)
    cursor = conn.cursor()

    # Buscar medio propio cuyo dominio coincida
    cursor.execute("""
        SELECT id FROM medios
        WHERE tipo = 'propio' AND %s ILIKE CONCAT('%%', REPLACE(REPLACE(REPLACE(REPLACE(url, 'https://', ''), 'http://', ''), 'www.', ''), '/', ''), '%%')
    """, (dominio_actual,))
    medio = cursor.fetchone()

    if not medio:
        conn.close()
        return []

    medio_id = medio[0]

    # Buscar competidores asociados
    cursor.execute("""
        SELECT m.nombre, m.url
        FROM competidores c
        JOIN medios m ON c.medio_competidor_id = m.id
        WHERE c.medio_padre_id = %s
    """, (medio_id,))
    resultados = cursor.fetchall()

    conn.close()
    return [{"nombre": nombre, "url": url} for nombre, url in resultados]
