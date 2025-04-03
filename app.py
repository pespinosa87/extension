from flask import Flask
from flask_cors import CORS
import os
import pytz
from apscheduler.schedulers.background import BackgroundScheduler

from config import Config
from controllers.api import api_bp
from controllers.web import web_bp
from services.scanner import init_scheduler

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

# Registrar blueprints
app.register_blueprint(web_bp)
app.register_blueprint(api_bp, url_prefix='/api')

# Iniciar scheduler
scheduler = init_scheduler()

@app.before_first_request
def before_first_request():
    print("Base de datos inicializada correctamente")
    print("Iniciando programador de tareas...")
    scheduler.start()
    print("Programador iniciado correctamente")

if __name__ == '__main__':
    scheduler.start()  # Iniciar el programador
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))