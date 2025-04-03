# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
import pytz
import requests
from bs4 import BeautifulSoup
import datetime
import sqlite3
import os
import time

scheduler = BackgroundScheduler(timezone=pytz.UTC)
scheduler.add_job(escanear_todos_los_medios, 'interval', hours=1)

app = Flask(__name__)
CORS(app)  # Habilitar CORS para permitir solicitudes desde la extensión

# Configuración de la base de datos
DATABASE = "temas_medios.db"

def init_db():
    conn = sqlite3.connect(DATABASE)
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

def obtener_temas_de_web(medio_id, url, selector_temas):
    """
    Extrae los temas y URLs del sitio web utilizando el selector CSS específico.
    
    Args:
        medio_id (int): ID del medio
        url (str): URL del sitio web
        selector_temas (str): Selector CSS para encontrar los temas
    
    Returns:
        list: Lista de tuplas (nombre_tema, url_tema)
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        temas_elementos = soup.select(selector_temas)
        
        temas = []
        for elemento in temas_elementos:
            if elemento.name == 'a':
                nombre = elemento.text.strip()
                url_tema = elemento.get('href', '')
                if not url_tema.startswith(('http://', 'https://')):
                    # Convertir URL relativa a absoluta
                    base_url = '/'.join(url.split('/')[:3])  # Extraer dominio
                    url_tema = f"{base_url}{url_tema if url_tema.startswith('/') else '/' + url_tema}"
                
                temas.append((nombre, url_tema))
            
        return temas
    
    except Exception as e:
        print(f"Error al obtener temas de {url}: {str(e)}")
        return []

def actualizar_temas_en_db(medio_id, temas_actuales):
    """
    Actualiza la base de datos con los temas encontrados.
    
    Args:
        medio_id (int): ID del medio
        temas_actuales (list): Lista de tuplas (nombre_tema, url_tema)
    """
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Obtener temas existentes para este medio
    cursor.execute("SELECT nombre, url, primera_vez FROM temas WHERE medio_id = ?", (medio_id,))
    temas_existentes = {(nombre, url): primera_vez for nombre, url, primera_vez in cursor.fetchall()}
    
    # Timestamp actual
    now = datetime.datetime.now().isoformat()
    
    # Actualizar o insertar temas actuales
    for nombre, url in temas_actuales:
        if (nombre, url) in temas_existentes:
            # El tema ya existe, actualizar última vez
            cursor.execute(
                "UPDATE temas SET ultima_vez = ? WHERE medio_id = ? AND nombre = ? AND url = ?",
                (now, medio_id, nombre, url)
            )
        else:
            # Nuevo tema, insertar
            cursor.execute(
                "INSERT INTO temas (medio_id, nombre, url, primera_vez, ultima_vez) VALUES (?, ?, ?, ?, ?)",
                (medio_id, nombre, url, now, now)
            )
    
    conn.commit()
    conn.close()

def escanear_todos_los_medios():
    """Función para escanear todos los medios registrados"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, nombre, url FROM medios")
    medios = cursor.fetchall()
    
    for medio_id, nombre, url in medios:
        # Aquí definimos los selectores para cada medio
        # En una implementación real, podrías tener esto en la base de datos
        selector = ".tema-destacado a"  # Selector genérico, ajustar según cada sitio
        
        print(f"Escaneando medio: {nombre} ({url})")
        temas = obtener_temas_de_web(medio_id, url, selector)
        actualizar_temas_en_db(medio_id, temas)
    
    conn.close()
    print(f"Escaneo completado a las {datetime.datetime.now()}")

# Configurar el programador para escanear cada hora
scheduler = BackgroundScheduler()
scheduler.add_job(escanear_todos_los_medios, 'interval', hours=1)

# Rutas de la API
@app.route('/api/medios', methods=['GET'])
def listar_medios():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, url, tipo FROM medios")
    medios = [{'id': row[0], 'nombre': row[1], 'url': row[2], 'tipo': row[3]} for row in cursor.fetchall()]
    conn.close()
    return jsonify(medios)

@app.route('/api/medios', methods=['POST'])
def agregar_medio():
    data = request.json
    if not data or 'nombre' not in data or 'url' not in data or 'tipo' not in data:
        return jsonify({'error': 'Datos incompletos'}), 400
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO medios (nombre, url, tipo) VALUES (?, ?, ?)",
            (data['nombre'], data['url'], data['tipo'])
        )
        conn.commit()
        medio_id = cursor.lastrowid
        conn.close()
        return jsonify({'id': medio_id, 'mensaje': 'Medio agregado correctamente'}), 201
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': 'El medio ya existe'}), 409

@app.route('/api/temas', methods=['GET'])
def obtener_temas():
    tipo_medio = request.args.get('tipo', 'todos')
    
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Para obtener resultados como diccionarios
    cursor = conn.cursor()
    
    query = """
    SELECT t.id, t.nombre, t.url, t.primera_vez, t.ultima_vez, m.nombre as medio, m.tipo as tipo_medio
    FROM temas t
    JOIN medios m ON t.medio_id = m.id
    """
    
    params = ()
    if tipo_medio != 'todos':
        query += " WHERE m.tipo = ?"
        params = (tipo_medio,)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    # Convertir a lista de diccionarios
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
        elif duracion_horas < 24:
            estado = "amarillo"
        else:
            estado = "rojo"
        
        temas.append({
            'id': row['id'],
            'nombre': row['nombre'],
            'url': row['url'],
            'primera_vez': row['primera_vez'],
            'ultima_vez': row['ultima_vez'],
            'medio': row['medio'],
            'tipo_medio': row['tipo_medio'],
            'duracion_horas': round(duracion_horas, 1),
            'estado': estado
        })
    
    conn.close()
    return jsonify(temas)

@app.route('/api/iniciar-escaneo', methods=['POST'])
def iniciar_escaneo_manual():
    """Endpoint para iniciar un escaneo manual"""
    try:
        escanear_todos_los_medios()
        return jsonify({'mensaje': 'Escaneo manual iniciado correctamente'}), 200
    except Exception as e:
        return jsonify({'error': f'Error al iniciar escaneo: {str(e)}'}), 500

@app.route('/api/agregar-medios-iniciales', methods=['POST'])
def agregar_medios_iniciales():
    """Endpoint para agregar una lista inicial de medios"""
    data = request.json
    if not data or 'medios' not in data:
        return jsonify({'error': 'Datos incompletos'}), 400
    
    medios = data['medios']
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    medios_agregados = 0
    medios_existentes = 0
    
    for medio in medios:
        if 'nombre' not in medio or 'url' not in medio or 'tipo' not in medio:
            continue
        
        try:
            cursor.execute(
                "INSERT INTO medios (nombre, url, tipo) VALUES (?, ?, ?)",
                (medio['nombre'], medio['url'], medio['tipo'])
            )
            medios_agregados += 1
        except sqlite3.IntegrityError:
            medios_existentes += 1
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'mensaje': f'Proceso completado. Medios agregados: {medios_agregados}, ya existentes: {medios_existentes}'
    }), 200

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint de verificación de salud para Render"""
    return jsonify({'status': 'ok'}), 200

# Inicializar la base de datos y el programador al iniciar la aplicación
@app.before_first_request
def before_first_request():
    init_db()
    scheduler.start()

# Para ejecución local
if __name__ == '__main__':
    init_db()  # Inicializar la base de datos
    scheduler.start()  # Iniciar el programador
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))