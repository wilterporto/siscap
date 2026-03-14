import os

class Config:
    SECRET_KEY = os.environ.get('63f4945d921d599f27ae4fdf5bada3f1') or 'voce-nunca-vai-adivinhar-esta-chave-secreta'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Use absolute path for SQLite on PythonAnywhere to avoid issues
    basedir = os.path.abspath(os.path.dirname(__file__))
    
    # Tratamento da URI do banco de dados para o Render (PostgreSQL)
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        # Tratar caracteres especiais na senha da URL de forma ultra-robusta
        import re
        from urllib.parse import quote, unquote
        
        # Regex para capturar: protocolo, usuário, senha (até o último @) e o resto do host
        pattern = r"^(?P<proto>postgresql://|postgres://)(?P<user>[^:]+):(?P<pass>.+)@(?P<rest>.+)$"
        match = re.match(pattern, db_url)
        
        if match:
            # Pegamos o que está entre o primeiro ':' e o último '@' como a senha
            raw_pass = match.group('pass')
            # Codificamos a senha (unquote primeiro para não codificar o que já está certo)
            encoded_pass = quote(unquote(raw_pass))
            # Remontamos a URL
            db_url = f"postgresql://{match.group('user')}:{encoded_pass}@{match.group('rest')}"
        elif db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        
    SQLALCHEMY_DATABASE_URI = db_url or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'siscap.db')

    # Configurações para estabilidade de conexão (especialmente para PostgreSQL/Supabase no Render)
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 280,
    }

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
