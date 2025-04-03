from flask import Blueprint, request, jsonify
from models.medio import get_all_medios, add_medio
from models.tema import get_temas
from services.scanner import escanear_todos_los_medios, agregar_medios_prensa

api_bp = Blueprint('api', __name__)

@api_bp.route('/medios', methods=['GET'])
def listar_medios():
    medios = get_all_medios()
    return jsonify(medios)

@api_bp.route('/medios', methods=['POST'])
def agregar_medio():
    data = request.json
    if not data or 'nombre' not in data or 'url' not in data or 'tipo' not in data:
        return jsonify({'error': 'Datos incompletos'}), 400
    
    return add_medio(data['nombre'], data['url'], data['tipo'])

@api_bp.route('/temas', methods=['GET'])
def obtener_temas():
    tipo_medio = request.args.get('tipo', 'todos')
    temas = get_temas(tipo_medio)
    return jsonify(temas)

@api_bp.route('/iniciar-escaneo', methods=['GET', 'POST'])
def iniciar_escaneo_manual():
    """Endpoint para iniciar un escaneo manual"""
    try:
        resultado = escanear_todos_los_medios()
        return jsonify({'mensaje': 'Escaneo manual completado correctamente', 'resultado': resultado}), 200
    except Exception as e:
        return jsonify({'error': f'Error al iniciar escaneo: {str(e)}'}), 500

@api_bp.route('/agregar-medios-prensa', methods=['GET', 'POST'])
def agregar_medios_prensa_endpoint():
    """Endpoint para agregar los medios de prensa proporcionados"""
    resultado = agregar_medios_prensa()
    return jsonify(resultado), 200

@api_bp.route('/agregar-medios-iniciales', methods=['POST'])
def agregar_medios_iniciales():
    """Endpoint para agregar una lista inicial de medios"""
    data = request.json
    if not data or 'medios' not in data:
        return jsonify({'error': 'Datos incompletos'}), 400
    
    medios = data['medios']
    medios_agregados = 0
    medios_existentes = 0
    
    for medio in medios:
        if 'nombre' not in medio or 'url' not in medio or 'tipo' not in medio:
            continue
        
        resultado, status_code = add_medio(medio['nombre'], medio['url'], medio['tipo'])
        if status_code == 201:
            medios_agregados += 1
        else:
            medios_existentes += 1
    
    return jsonify({
        'mensaje': f'Proceso completado. Medios agregados: {medios_agregados}, ya existentes: {medios_existentes}'
    }), 200