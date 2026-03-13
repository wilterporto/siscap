import os

class Config:
    SECRET_KEY = os.environ.get('63f4945d921d599f27ae4fdf5bada3f1') or 'voce-nunca-vai-adivinhar-esta-chave-secreta'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Use absolute path for SQLite on PythonAnywhere to avoid issues
    basedir = os.path.abspath(os.path.dirname(__file__))
    
    # Tratamento da URI do banco de dados para o Render (PostgreSQL)
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        
        # Tratar caracteres especiais na senha da URL caso necessário
        from urllib.parse import urlparse, urlunparse, quote, unquote
        try:
            p = urlparse(db_url)
            if p.password:
                # Decodifica caso já esteja codificado e codifica novamente para garantir padrão
                new_password = quote(unquote(p.password))
                # Reconstrói a parte netloc com a senha segura
                user_info = p.username
                if new_password:
                    user_info = f"{p.username}:{new_password}"
                new_netloc = f"{user_info}@{p.hostname}"
                if p.port:
                    new_netloc += f":{p.port}"
                
                db_url = urlunparse(p._replace(netloc=new_netloc))
        except Exception:
            pass # Mantém original em caso de erro no parse
        
    SQLALCHEMY_DATABASE_URI = db_url or \
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
