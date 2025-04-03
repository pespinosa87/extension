from flask import Blueprint, render_template, jsonify, request
import datetime
from models.medio import get_medio_stats, get_all_medios
from models.tema import get_temas, get_tema_stats
from config import Config

web_bp = Blueprint('web', __name__)

@web_bp.route('/')
def index():
    return render_template('index.html')

@web_bp.route('/visualizar')
def visualizar_temas():
    medio_id = request.args.get('medio_id', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page

    medios_stats = get_medio_stats()
    temas_stats = get_tema_stats()
    temas = get_temas(limit=per_page, offset=offset, medio_id=medio_id)
    todos_los_medios = get_all_medios()

    return render_template(
        'visualizar.html',
        temas=temas,
        medios_stats=medios_stats,
        temas_stats=temas_stats,
        timestamp=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        medios=todos_los_medios,
        medio_seleccionado=medio_id,
        page=page
    )


@web_bp.route('/health')
def health_check():
    try:
        medios_stats = get_medio_stats()
        temas_stats = get_tema_stats()
        
        return jsonify({
            'status': 'ok',
            'database': {
                'path': Config.DATABASE,
                'medios_count': medios_stats['total'],
                'temas_count': temas_stats['total']
            }
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'database_path': Config.DATABASE
        }), 500