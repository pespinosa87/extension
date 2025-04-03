# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import datetime
import sqlite3
import os
import time
import pytz
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
CORS(app)  # Habilitar CORS para permitir solicitudes desde la extensión

# Configuración de la base de datos
# Usar directorio persistente en Render
import os
# Render proporciona el directorio /var/data/ para almacenamiento persistente
DATABASE_DIR = '/var/data' if os.path.exists('/var/data') else '.'
os.makedirs(DATABASE_DIR, exist_ok=True)
DATABASE = os.path.join(DATABASE_DIR, "temas_medios.db")
print(f"Usando base de datos en: {DATABASE}")

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

def obtener_temas_de_web(medio_id, url, selector_temas=None):
    """
    Extrae los temas y URLs del sitio web utilizando el selector CSS específico.
    
    Args:
        medio_id (int): ID del medio
        url (str): URL del sitio web
        selector_temas (str, optional): Selector CSS personalizado. Si es None, 
                                        se usa el selector por defecto según el tipo de medio.
    
    Returns:
        list: Lista de tuplas (nombre_tema, url_tema)
    """
    try:
        # Configurar headers para simular un navegador real
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Obtener el contenido de la página
        print(f"Obteniendo contenido de {url}...")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Si no se proporciona selector, obtener el selector predeterminado
        if not selector_temas:
            # Verificar si es un medio propio basado en los dominios proporcionados
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute("SELECT tipo FROM medios WHERE id = ?", (medio_id,))
            tipo_medio = cursor.fetchone()[0]
            conn.close()
            
            if tipo_medio == 'propio':
                # Para medios propios, usar el selector específico mencionado
                selector_temas = ".ft-org-header-regionales-menu-panel__tagbar a"
            else:
                # Para competencia, usar un selector genérico (debe ajustarse según el medio)
                selector_temas = "a.tag, a.tema, .tags a"  # Ejemplos genéricos
        
        print(f"Usando selector: {selector_temas}")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extraer temas
        temas_elementos = soup.select(selector_temas)
        print(f"Encontrados {len(temas_elementos)} elementos con el selector")
        
        temas = []
        for elemento in temas_elementos:
            nombre = elemento.text.strip()
            url_tema = elemento.get('href', '')
            
            # Si la URL es relativa, convertirla a absoluta
            if url_tema and not url_tema.startswith(('http://', 'https://')):
                base_url = '/'.join(url.split('/')[:3])  # Extraer dominio
                url_tema = f"{base_url}{url_tema if url_tema.startswith('/') else '/' + url_tema}"
            
            if nombre and url_tema:  # Solo agregar si tiene nombre y URL
                temas.append((nombre, url_tema))
                print(f"Tema encontrado: {nombre} -> {url_tema}")
        
        return temas
    
    except Exception as e:
        print(f"Error al obtener temas de {url}: {str(e)}")
        import traceback
        traceback.print_exc()
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
    print(f"Iniciando escaneo a las {datetime.datetime.now()}")
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, nombre, url, tipo FROM medios")
    medios = cursor.fetchall()
    conn.close()
    
    total_medios = len(medios)
    medios_procesados = 0
    temas_encontrados = 0
    
    for medio_id, nombre, url, tipo in medios:
        print(f"[{medios_procesados+1}/{total_medios}] Escaneando medio: {nombre} ({url}) - Tipo: {tipo}")
        
        # Llamar a la función con el selector predeterminado (None)
        temas = obtener_temas_de_web(medio_id, url)
        
        if temas:
            actualizar_temas_en_db(medio_id, temas)
            temas_encontrados += len(temas)
            print(f"✓ Encontrados {len(temas)} temas en {nombre}")
        else:
            print(f"✗ No se encontraron temas en {nombre}")
        
        medios_procesados += 1
    
    print(f"Escaneo completado a las {datetime.datetime.now()}")
    print(f"Resumen: {medios_procesados} medios procesados, {temas_encontrados} temas encontrados en total")
    
    return {
        "medios_procesados": medios_procesados,
        "temas_encontrados": temas_encontrados
    }

# Configurar el programador para escanear cada hora
scheduler = BackgroundScheduler(timezone=pytz.UTC)
scheduler.add_job(escanear_todos_los_medios, 'interval', hours=1)

# Rutas de la API
@app.route('/', methods=['GET'])
def index():
    """Página de inicio para la aplicación"""
    return """
    <html>
    <head>
        <title>API de Temas Digitales</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                line-height: 1.6;
                margin: 0;
                padding: 20px;
                color: #333;
            }
            .container {
                max-width: 800px;
                margin: 0 auto;
                background: #f9f9f9;
                padding: 20px;
                border-radius: 5px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }
            h1 {
                color: #2c3e50;
                border-bottom: 1px solid #eee;
                padding-bottom: 10px;
            }
            h2 {
                color: #3498db;
                margin-top: 20px;
            }
            code {
                background: #f4f4f4;
                padding: 2px 5px;
                border-radius: 3px;
                font-family: monospace;
            }
            ul {
                padding-left: 20px;
            }
            .endpoint {
                margin-bottom: 15px;
                padding: 10px;
                background: #f0f8ff;
                border-left: 4px solid #3498db;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>API de Temas Digitales</h1>
            <p>Esta es la API para el monitor de temas destacados en medios digitales.</p>
            
            <h2>Endpoints disponibles:</h2>
            
            <div class="endpoint">
                <p><code>GET /health</code> - Verificar el estado de la aplicación</p>
                <p>Ejemplo: <a href="/health">/health</a></p>
            </div>
            
            <div class="endpoint">
                <p><code>GET /api/medios</code> - Listar todos los medios registrados</p>
                <p>Ejemplo: <a href="/api/medios">/api/medios</a></p>
            </div>
            
            <div class="endpoint">
                <p><code>GET /api/temas</code> - Obtener todos los temas</p>
                <p>Ejemplo: <a href="/api/temas">/api/temas</a></p>
            </div>
            
            <div class="endpoint">
                <p><code>GET /api/temas?tipo=propio</code> - Filtrar temas por tipo de medio</p>
                <p>Ejemplo: <a href="/api/temas?tipo=propio">/api/temas?tipo=propio</a></p>
            </div>
            
            <div class="endpoint">
                <p><code>GET /visualizar</code> - Ver una página con los temas monitoreados</p>
                <p>Ejemplo: <a href="/visualizar">/visualizar</a></p>
            </div>
            
            <h2>Uso con la extensión de Chrome:</h2>
            <p>Esta API está diseñada para ser utilizada con la extensión de Chrome para monitorización de temas destacados.</p>
            <p>Para configurar la extensión, utiliza la siguiente URL como base de la API:</p>
            <code>https://extension-m7fx.onrender.com/api</code>
        </div>
    </body>
    </html>
    """

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
        resultado = escanear_todos_los_medios()
        return jsonify({'mensaje': 'Escaneo manual completado correctamente', 'resultado': resultado}), 200
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

@app.route('/api/agregar-medios-prensa', methods=['GET', 'POST'])
def agregar_medios_prensa():
    """Endpoint para agregar los medios de prensa proporcionados"""
    # Lista de medios propios
    medios_propios = [
        {"nombre": "Diari de Girona", "url": "https://www.diaridegirona.cat/", "tipo": "propio"},
        {"nombre": "Diario Córdoba", "url": "https://www.diariocordoba.com/", "tipo": "propio"},
        {"nombre": "Diario de Ibiza", "url": "https://www.diariodeibiza.es/", "tipo": "propio"},
        {"nombre": "Información", "url": "https://www.informacion.es/", "tipo": "propio"},
        {"nombre": "Diario de Mallorca", "url": "https://www.diariodemallorca.es/", "tipo": "propio"},
        {"nombre": "El Día", "url": "https://www.eldia.es/", "tipo": "propio"},
        {"nombre": "Empordà", "url": "https://www.emporda.info/", "tipo": "propio"},
        {"nombre": "El Periódico de Aragón", "url": "https://www.elperiodicodearagon.com/", "tipo": "propio"},
        {"nombre": "El Periódico Extremadura", "url": "https://www.elperiodicoextremadura.com/", "tipo": "propio"},
        {"nombre": "El Periódico Mediterráneo", "url": "https://www.elperiodicomediterraneo.com/", "tipo": "propio"},
        {"nombre": "Faro de Vigo", "url": "https://www.farodevigo.es/", "tipo": "propio"},
        {"nombre": "La Crónica de Badajoz", "url": "https://www.lacronicabadajoz.com/", "tipo": "propio"},
        {"nombre": "La Nueva España", "url": "https://www.lne.es/", "tipo": "propio"},
        {"nombre": "La Opinión A Coruña", "url": "https://www.laopinioncoruna.es/", "tipo": "propio"},
        {"nombre": "La Opinión de Murcia", "url": "https://www.laopiniondemurcia.es/", "tipo": "propio"},
        {"nombre": "La Opinión de Málaga", "url": "https://www.laopiniondemalaga.es/", "tipo": "propio"},
        {"nombre": "La Opinión de Zamora", "url": "https://www.laopiniondezamora.es/", "tipo": "propio"},
        {"nombre": "La Provincia", "url": "https://www.laprovincia.es/", "tipo": "propio"},
        {"nombre": "Levante-EMV", "url": "https://www.levante-emv.com/", "tipo": "propio"},
        {"nombre": "Mallorca Zeitung", "url": "https://www.mallorcazeitung.es/", "tipo": "propio"},
        {"nombre": "Regió7", "url": "https://www.regio7.cat/", "tipo": "propio"},
        {"nombre": "Superdeporte", "url": "https://www.superdeporte.es/", "tipo": "propio"},
        {"nombre": "El Correo Gallego", "url": "https://www.elcorreogallego.es/", "tipo": "propio"},
        {"nombre": "El Correo Web", "url": "https://www.elcorreoweb.es/", "tipo": "propio"},
        {"nombre": "EPE", "url": "https://www.epe.es/es/", "tipo": "propio"},
        {"nombre": "El Periódico", "url": "https://www.elperiodico.com/es/", "tipo": "propio"},
        {"nombre": "Sport", "url": "https://www.sport.es/es/", "tipo": "propio"}
    ]
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    medios_agregados = 0
    medios_existentes = 0
    
    for medio in medios_propios:
        try:
            cursor.execute(
                "INSERT INTO medios (nombre, url, tipo) VALUES (?, ?, ?)",
                (medio["nombre"], medio["url"], medio["tipo"])
            )
            medios_agregados += 1
        except sqlite3.IntegrityError:
            medios_existentes += 1
    
    conn.commit()
    conn.close()
    
    # Iniciar un escaneo después de agregar los medios
    resultado_escaneo = {}
    try:
        resultado_escaneo = escanear_todos_los_medios()
    except Exception as e:
        resultado_escaneo = {"error": str(e)}
    
    return jsonify({
        "mensaje": f"Proceso completado. Medios agregados: {medios_agregados}, ya existentes: {medios_existentes}",
        "resultado_escaneo": resultado_escaneo
    }), 200

@app.route('/visualizar', methods=['GET'])
def visualizar_temas():
    """Página para visualizar los temas monitoreados"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Obtener información sobre medios
    cursor.execute("SELECT COUNT(*) as total FROM medios")
    total_medios = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as total FROM medios WHERE tipo = 'propio'")
    medios_propios = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as total FROM medios WHERE tipo = 'competencia'")
    medios_competencia = cursor.fetchone()['total']
    
    # Obtener información sobre temas
    cursor.execute("SELECT COUNT(*) as total FROM temas")
    total_temas = cursor.fetchone()['total']
    
    # Obtener todos los temas con información del medio
    cursor.execute("""
        SELECT t.id, t.nombre, t.url, t.primera_vez, t.ultima_vez, 
               m.nombre as medio_nombre, m.url as medio_url, m.tipo as medio_tipo
        FROM temas t
        JOIN medios m ON t.medio_id = m.id
        ORDER BY t.ultima_vez DESC
        LIMIT 100
    """)
    temas = cursor.fetchall()
    
    # Procesar temas para mostrar
    temas_procesados = []
    for tema in temas:
        primera_vez = datetime.datetime.fromisoformat(tema['primera_vez'])
        ultima_vez = datetime.datetime.fromisoformat(tema['ultima_vez'])
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
        
        temas_procesados.append({
            'id': tema['id'],
            'nombre': tema['nombre'],
            'url': tema['url'],
            'primera_vez': primera_vez.strftime('%Y-%m-%d %H:%M:%S'),
            'ultima_vez': ultima_vez.strftime('%Y-%m-%d %H:%M:%S'),
            'medio_nombre': tema['medio_nombre'],
            'medio_url': tema['medio_url'],
            'medio_tipo': tema['medio_tipo'],
            'duracion_horas': round(duracion_horas, 1),
            'estado': estado,
            'color': color
        })
    
    conn.close()
    
    # Generar HTML
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Visualización de Temas Monitoreados</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                margin: 0;
                padding: 20px;
                color: #333;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
            }}
            header {{
                background-color: #4285f4;
                color: white;
                padding: 15px;
                margin-bottom: 20px;
                border-radius: 5px;
            }}
            h1, h2 {{
                margin: 0;
            }}
            .stats {{
                display: flex;
                flex-wrap: wrap;
                margin-bottom: 20px;
                gap: 15px;
            }}
            .stat-card {{
                background-color: #f5f5f5;
                border-radius: 5px;
                padding: 15px;
                flex: 1;
                min-width: 200px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }}
            .stat-card h3 {{
                margin-top: 0;
                border-bottom: 1px solid #ddd;
                padding-bottom: 10px;
            }}
            .number {{
                font-size: 2em;
                font-weight: bold;
                color: #4285f4;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 10px;
                text-align: left;
            }}
            th {{
                background-color: #f2f2f2;
            }}
            tr:hover {{
                background-color: #f5f5f5;
            }}
            .tema-tag {{
                display: inline-block;
                padding: 5px 10px;
                border-radius: 3px;
                color: white;
                font-weight: bold;
            }}
            .actions {{
                margin: 20px 0;
                display: flex;
                gap: 10px;
            }}
            button {{
                padding: 10px 15px;
                background-color: #4285f4;
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
            }}
            button:hover {{
                background-color: #3b78e7}}
            .refresh {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
            }}
            .refresh small {{
                color: #666;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Monitor de Temas Digitales</h1>
                <p>Visualización de temas destacados en medios digitales</p>
            </header>
            
            <div class="stats">
                <div class="stat-card">
                    <h3>Medios monitoreados</h3>
                    <div class="number">{total_medios}</div>
                    <div>Propios: {medios_propios}</div>
                    <div>Competencia: {medios_competencia}</div>
                </div>
                
                <div class="stat-card">
                    <h3>Temas encontrados</h3>
                    <div class="number">{total_temas}</div>
                    <div>Últimos 100 temas mostrados</div>
                </div>
            </div>
            
            <div class="actions">
                <button onclick="location.href='/api/iniciar-escaneo'" type="button">Iniciar escaneo manual</button>
                <button onclick="location.href='/api/agregar-medios-prensa'" type="button">Cargar medios de prensa</button>
                <button onclick="location.href='/visualizar'" type="button">Actualizar página</button>
            </div>
            
            <div class="refresh">
                <h2>Temas monitoreados</h2>
                <small>Última actualización: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</small>
            </div>
            
            <table>
                <thead>
                    <tr>
                        <th>Tema</th>
                        <th>Medio</th>
                        <th>Tipo</th>
                        <th>Tiempo</th>
                        <th>Estado</th>
                        <th>Última actualización</th>
                        <th>Acciones</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    # Añadir filas de datos
    if temas_procesados:
        for tema in temas_procesados:
            html += f"""
                    <tr>
                        <td>{tema['nombre']}</td>
                        <td><a href="{tema['medio_url']}" target="_blank">{tema['medio_nombre']}</a></td>
                        <td>{tema['medio_tipo']}</td>
                        <td>{tema['duracion_horas']} horas</td>
                        <td><span class="tema-tag" style="background-color: {tema['color']}">{tema['estado'].upper()}</span></td>
                        <td>{tema['ultima_vez']}</td>
                        <td><a href="{tema['url']}" target="_blank">Ver noticia</a></td>
                    </tr>
            """
    else:
        html += """
                    <tr>
                        <td colspan="7" style="text-align: center;">No hay temas monitoreados aún. Inicia un escaneo manual o carga los medios de prensa.</td>
                    </tr>
        """
    
    html += """
                </tbody>
            </table>
        </div>
        
        <script>
            // Auto-refresh every 5 minutes
            setTimeout(() => {
                window.location.reload();
            }, 5 * 60 * 1000);
        </script>
    </body>
    </html>
    """
    
    return html

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint de verificación de salud para Render"""
    try:
        # Verificar si la base de datos existe y tiene las tablas necesarias
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Comprobar tablas existentes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        # Contar registros
        medios_count = 0
        temas_count = 0
        if 'medios' in tables:
            cursor.execute("SELECT COUNT(*) FROM medios")
            medios_count = cursor.fetchone()[0]
        if 'temas' in tables:
            cursor.execute("SELECT COUNT(*) FROM temas")
            temas_count = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'status': 'ok',
            'database': {
                'path': DATABASE,
                'tables': tables,
                'medios_count': medios_count,
                'temas_count': temas_count
            }
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'database_path': DATABASE
        }), 500

@app.before_first_request
def before_first_request():
    print("Inicializando base de datos...")
    init_db()
    print("Base de datos inicializada correctamente")
    print("Iniciando programador de tareas...")
    scheduler.start()
    print("Programador iniciado correctamente")

# Para ejecución local
if __name__ == '__main__':
    init_db()  # Inicializar la base de datos
    scheduler.start()  # Iniciar el programador
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))