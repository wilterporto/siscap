# Deploy do SISCAP no PythonAnywhere

Este guia descreve como configurar o ambiente de produção para o sistema **SISCAP** na plataforma PythonAnywhere. O PythonAnywhere oferece um banco de dados SQLite interno e espaço em disco persistente suficiente, portanto este método é simples e gratuito.

## 1. Preparação
1. Crie uma conta gratuita no [PythonAnywhere](https://www.pythonanywhere.com/).
2. Faça login e vá para o menu principal (**Dashboard**).
3. Abra um **Bash Console** clicando em "Bash" na seção *New console*.

## 2. Clonar ou Fazer Upload do Projeto
No console bash, digite os comandos abaixo (substitua `<url_do_seu_repositorio>` pelo link do GitHub do projeto):

```bash
cd ~
git clone <url_do_seu_repositorio> siscap
```
*(Se você não usa git, você pode zipar os arquivos na sua máquina, fazer o upload pela aba "Files" da plataforma, descompactar e dar o nome da pasta de `siscap`.)*

## 3. Configurar o Ambiente Virtual (venv)
Ainda no console bash:

```bash
cd ~/siscap
# Criar o virtual environment (ambiente isolado) com o Python desejado (ex: 3.10)
mkvirtualenv --python=/usr/bin/python3.10 venv_siscap

# Após criar, o ambiente já estará ativado.
# Instale as bibliotecas necessárias listadas no requirements.txt
pip install -r requirements.txt
```

## 4. Configurar App na Plataforma Web
1. Vá para a aba **Web** no dashboard lateral ou principal do PythonAnywhere.
2. Clique no botão **"Add a new web app"**.
3. Na primeira tela, ignore domínios personalizados (no plano free clica em **Next**).
4. **MUITO IMPORTANTE:** Na escolha de frameworks, escolha **Configuração Manual (Manual Configuration)** e NÃO escolha Flask. Em seguida certifique a versão do Python correta (Ex: 3.10).
5. O aplicativo básico não fará nada até configurarmos os passos a seguir.

## 5. Configurar o arquivo WSGI
1. Na mesma aba **Web**, desça a página até a seção **Code**.
2. Clique no link do arquivo listado em **WSGI configuration file** (Ex: `/var/www/seu_usuario_pythonanywhere_com_wsgi.py`).
3. Uma tela de editor de texto será aberta. **Apague todo o conteúdo** que veio como padrão no arquivo.
4. Volte à pasta do seu projeto e copie todo o conteúdo do arquivo `pythonanywhere_wsgi_example.py` e **cole neste arquivo online**.
5. **ATENÇÃO:** No arquivo colado, há uma linha de código apontando o diretório `path = '/home/seu_usuario/siscap'`. Altere a palavra `seu_usuario` pelo nome correto da sua conta (username) do PythonAnywhere existente na URL no topo do seu editor.
6. Clique em **Save** no canto superior direito do editor.

## 6. Configurar o Virtualenv na Tela Web
1. Ainda na aba **Web**, desça até a opção **Virtualenv** (quase no final da página) e adicione o diretório responsável pelo pacote de dependências PIP criados no passo 3.
   - O caminho deve ser preenchido como: `/home/<seu_usuario>/.virtualenvs/venv_siscap` (lembre-se de usar seu username real no `<seu_usuario>`).

## 7. Banco de Dados Inicial
Agora volte ao **Bash Console** antigo (ou abra um novo) para criar o banco de dados interno ativando sua tabela inicial com o admin:

```bash
cd ~/siscap
# Ativar o ambiente se o console foi fechado anteriormente
workon venv_siscap

# Inicializar Banco de Dados do SQLAlchemy via console interativo do Python
python
>>> from app import db, create_app
>>> app = create_app()
>>> with app.app_context():
...     db.create_all()
...
>>> exit()

# Criar Usuário Administrador Interativamente
export FLASK_APP=app.py
flask create-admin
```
O console te fará perguntas sobre os dados do seu Admin (Nome, CPF e Senha).

## 8. Arquivos Estáticos (Estilo/CSS/Imagens)
Para que os layouts HTML renderizem e carreguem as imagens configuradas sem conflitos de servidor, é necessário dizer ao PythonAnywhere onde as imagens do Flask residem.
Na aba **Web**, desça até se encontrar em **Static files** (arquivos estáticos) e defina estes mapeamentos clicando no link para criar nova entrada:

*Clique em "Enter URL" e "Enter path" respectivamente para os dados da tabela abaixo:*

| URL (Padrão URL) | (Path/Directory) |
| --- | --- |
| `/static/` | `/home/<seu_usuario>/siscap/static` |

## 9. Finalizar Deploy Segurado SSL
1. No início do formulário da aba **Web**, navegue até a sub-seção **Security** e marque "Ativado" ou "Habilitado" na opção **Force HTTPS**.
2. Por fim, volte mais próximo ao topo e clique no botão verde rotulado **"Reload <seu_site>"**.
3. Acesse seu site com layout pronto em `https://<seu_usuario>.pythonanywhere.com`.

## Lembretes de Segurança
- O `SECRET_KEY` no interior da instrução do `pythonanywhere_wsgi_example.py` que você acabou de usar deve idealmente ser atualizado no arquivo para qualquer código randômico antes ou após a subida visando encriptação apropriada nos cookies dos usuários (sistemas de login).
- Como o script de código que faz a ponte (wsgi) invoca o aplicativo utilizando o `create_app()` sem invocações nativas `.run()`, o ambiente já está apto aos níveis exigidos para Produção (`DEBUG=False`), isentos dos avisos padrões de segurança de console que poderiam estar expostos indevidamente.
