
# +++++++++++ PYTHONANYWHERE WSGI CONFIG +++++++++++
# ++++++++++++++++++++++++++++++++++++++++++++++++++
# Copie o conteúdo abaixo para o arquivo de configuração WSGI no PythonAnywhere
# (Geralmente localizado em: /var/www/<seu_usuario>_pythonanywhere_com_wsgi.py)

import sys
import os

# Adicione o caminho do seu projeto
# Substitua 'seu_usuario' pelo seu nome de usuário no PythonAnywhere
path = '/home/seu_usuario/siscap'
if path not in sys.path:
    sys.path.append(path)

# Defina variáveis de ambiente se necessário (Embora seja melhor usar .env)
os.environ['FLASK_ENV'] = 'production'
os.environ['SECRET_KEY'] = 'uma_chave_super_secreta_e_segura_aqui'
# Banco de dados: Se usar SQLite, garanta que o caminho seja absoluto e a pasta 'instance' exista.
# Exemplo para SQLite no PythonAnywhere:
instance_path = os.path.join(path, 'instance')
if not os.path.exists(instance_path):
    os.makedirs(instance_path)

db_path = os.path.join(instance_path, 'siscap.db')
os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'

from app import create_app
from config import ProductionConfig

# Crie a aplicação usando a configuração de produção
application = create_app(ProductionConfig)
