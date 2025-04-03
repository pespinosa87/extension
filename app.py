from flask import Flask
from flask_cors import CORS
import os

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

# Iniciar scheduler directamente (sin esperar a primera request)
scheduler = init_scheduler()
scheduler.start()
print("✅ Programador de tareas iniciado automáticamente")

@app.before_first_request
def before_first_request():
    print("✔️ App Flask iniciada correctamente")
