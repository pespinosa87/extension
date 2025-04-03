import os

class Config:
    # Configuración de la base de datos
    DATABASE_DIR = '/var/data' if os.path.exists('/var/data') else '.'
    DATABASE = os.path.join(DATABASE_DIR, "temas_medios.db")
    
    # Otras configuraciones
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-12345'
    DEBUG = os.environ.get('FLASK_ENV') != 'production'