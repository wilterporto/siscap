# Deploy do SISCAP no PythonAnywhere

Este guia descreve como configurar o ambiente de produção para o sistema SISCAP na plataforma PythonAnywhere.

## 1. Preparação
1. Crie uma conta no [PythonAnywhere](https://www.pythonanywhere.com/).
2. Faça login e vá para o **Console Tab**.
3. Abra um **Bash Console**.

## 2. Clonar o Projeto
No console bash, digite (substitua `<url_do_seu_repositorio>` pelo link do GitHub se tiver, ou faça upload dos arquivos na aba "Files"):

```bash
cd ~
# Se estiver usando git (recomendado):
git clone <url_do_seu_repositorio> siscap
# Se não usar git, faça upload dos arquivos para uma pasta chamada 'siscap'
```

## 3. Configurar Ambiente Virtual
```bash
cd ~/siscap
# Criar virtualenv com Python 3.10 (ou versão desejada)
mkvirtualenv --python=/usr/bin/python3.10 venv_siscap
# O ambiente ativará automaticamente
pip install -r requirements.txt
```

## 4. Configurar Web App
1. Vá para a aba **Web** no dashboard do PythonAnywhere.
2. Clique em **Add a new web app**.
3. Escolha **Manual configuration** (NÃO escolha Flask wizard, precisamos configurar manualmente).
4. Escolha a versão do Python correta (Ex: 3.10).

## 5. Configurar WSGI
1. Na aba Web, desça até a seção **Code**.
2. Clique no link para editar o arquivo **WSGI configuration file** (Ex: `/var/www/seu_usuario_pythonanywhere_com_wsgi.py`).
3. APAGUE TODO O CONTEÚDO e copie o conteúdo do arquivo `pythonanywhere_wsgi_example.py` que está no seu projeto.
4. **IMPORTANTE**: No arquivo colado, altere a linha `path = '/home/seu_usuario/siscap'` substituindo `seu_usuario` pelo seu nome de usuário real do PythonAnywhere.

## 6. Configurar Virtualenv na Web Tab
1. Na aba Web, seção **Virtualenv**, digite o caminho do seu ambiente virtual.
   - Deve ser: `/home/<seu_usuario>/.virtualenvs/venv_siscap` (verifique com `workon venv_siscap; which python` no console se tiver dúvida).

## 7. Banco de Dados Inicial
Volte ao **Bash Console**:
```bash
cd ~/siscap
# Ative o venv se não estiver ativo
workon venv_siscap

# Inicializar DB
python
>>> from app import db, create_app
>>> app = create_app()
>>> with app.app_context():
...     db.create_all()
...
>>> exit()

# Criar Admin
export FLASK_APP=app.py
flask create-admin
```

## 8. Arquivos Estáticos (CSS/JS)
Para o CSS funcionar, configure na aba **Web** -> **Static files**:

| URL | Directory |
| --- | --- |
| `/static/` | `/home/<seu_usuario>/siscap/static` |

## 9. Finalizar
1. Na aba **Web**, clique no botão verde **Reload <seu_site>**.
2. Acesse seu site (Ex: `https://<seu_usuario>.pythonanywhere.com`).
3. Force HTTPS na aba Web para segurança (opção "Force HTTPS").

## Segurança
- O `SECRET_KEY` no arquivo WSGI de exemplo deve ser alterado para algo único.
- O `DEBUG` está desativado por padrão na configuração `ProductionConfig`.
