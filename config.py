import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'voce-nunca-vai-adivinhar-esta-chave-secreta'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Use absolute path for SQLite on PythonAnywhere to avoid issues
    basedir = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'siscap.db')

    # Ensure JSON responses are not ASCII-escaped (allows UTF-8 characters)
    JSON_AS_ASCII = False

class ProductionConfig(Config):
    DEBUG = False
    # Ensure secure cookies if using HTTPS (PythonAnywhere handles HTTPS)
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True

class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False
