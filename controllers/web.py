from flask import Blueprint, render_template, request
from models.tema import get_temas_visualizacion
from models.medio import get_all_medios
import datetime

web_bp = Blueprint('web', __name__)

@web_bp.route('/')
def index():
    return render_template("index.html")

@web_bp.route('/health')
def health_check():
    return "OK"

@web_bp.route("/visualizar/")
def visualizar_temas():
    medio_id = request.args.get("medio_id", type=int)
    tipo = request.args.get("tipo", default="", type=str)
    page = request.args.get("page", default=1, type=int)
    visible = request.args.get("visible")  # 👈 Añadido

    temas, medios, stats = get_temas_visualizacion(
        medio_id=medio_id,
        tipo_medio=tipo if tipo != "todos" else "",
        visible=visible,  # 👈 Añadido
        page=page
    )

    return render_template(
        "visualizar.html",
        temas=temas,
        medios=medios,
        medios_stats=stats["medios"],
        temas_stats=stats["temas"],
        page=page,
        medio_seleccionado=medio_id,
        tipo_seleccionado=tipo,
        visible=visible  # 👈 Para que lo conserve en la vista
    )

