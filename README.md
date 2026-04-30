# SISCAP - Sistema de Controle de Alunos e Pastas

O **SISCAP** é uma aplicação web (PWA - Progressive Web App) construída para gerenciar alunos e suas respectivas pastas (caixas). Ele oferece um ambiente robusto e fácil de usar para administradores e usuários acompanharem cadastros, verificarem homônimos, gerenciarem caixas e realizarem controle de acessos com trilha de auditoria completa.

## 🚀 Funcionalidades Principais

- **Gestão de Alunos e Pastas**: Cadastro ágil de alunos atrelando-os a pastas organizacionais (caixas), com controle de capacidade.
- **PWA (Progressive Web App)**: Pode ser instalado como um aplicativo diretamente no computador ou dispositivo móvel, permitindo uma experiência mais imersiva (suporte a Service Worker e cache offline básico).
- **Painel Administrativo**: Visão completa dos dados através de gráficos e métricas, visualização de caixas lotadas, alertas sobre alunos homônimos e mais.
- **Controle de Acessos e Perfis**: Sistema de login seguro com perfis de Usuário e Administrador. 
- **Auditoria**: Log automático de atividades no sistema (criação, edição, exclusão de registros e logins) para garantir a segurança da informação.
- **Importação/Exportação**: Capacidade de lidar com processamento em lote via arquivos para importar e exportar os dados do sistema.
- **Zona de Perigo (Admin)**: Recurso para exclusão em massa de alunos e caixas exigindo um motivo justificado obrigatório, o qual fica gravado no registro de auditoria.

## 🛠️ Tecnologias Utilizadas

- **Back-end**: [Python](https://www.python.org/) e [Flask](https://flask.palletsprojects.com/)
- **Banco de Dados**: [SQLite](https://www.sqlite.org/) (desenvolvimento/produção padrão) com suporte ao [PostgreSQL](https://www.postgresql.org/) através do [SQLAlchemy](https://www.sqlalchemy.org/)
- **Front-end**: HTML5, CSS3, JavaScript Vanilla, Bootstrap 5, Jinja2 (Templates)
- **Outros**: Flask-Login, Werkzeug (segurança/hashes)

## 📦 Instalação e Execução Local

Siga os passos abaixo para configurar e rodar o projeto localmente:

### Pré-requisitos
- Python 3.8+ instalado
- Git

### Passo a Passo

1. **Clone o repositório:**
   ```bash
   git clone https://github.com/seu-usuario/siscap.git
   cd siscap
   ```

2. **Crie e ative um ambiente virtual:**
   - **Windows:**
     ```bash
     python -m venv .venv
     .venv\Scripts\activate
     ```
   - **Linux/Mac:**
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configuração de Variáveis de Ambiente:**
   Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis base:
   ```env
   FLASK_APP=app.py
   FLASK_ENV=development
   SECRET_KEY=sua_chave_secreta_super_segura
   # DATABASE_URL=postgresql://usuario:senha@localhost/siscap  # Opcional se for usar PostgreSQL
   ```

5. **Inicie o servidor local:**
   ```bash
   flask run
   # ou
   python app.py
   ```

6. **Acesse a aplicação:**
   Abra o navegador e acesse: `http://127.0.0.1:5000`

   > **Nota:** Se o banco de dados estiver limpo, a aplicação criará automaticamente um usuário administrador padrão na primeira execução:
   > - **Usuário:** `admin`
   > - **Senha:** `admin123`

## ☁️ Deploy (Implantação)

O projeto possui instruções e arquivos nativos prontos para deploy em plataformas de nuvem populares:

- **PythonAnywhere:** Veja o guia em `DEPLOY_PYTHONANYWHERE.md` e o script `pythonanywhere_wsgi_example.py`.
- **Render:** Veja o guia em `DEPLOY_RENDER.md` e a configuração base `render.yaml`.
- **Geral:** Dicas gerais em `DEPLOY.md`.

## 🔒 Regras de Negócio Importantes
- **Exclusões Sensíveis:** Determinadas ações como exclusão de todos os dados do banco só podem ser realizadas por perfis de `Administrador` e exigem uma justificativa obrigatória que servirá para auditoria interna.
- **Autenticação Segura:** Logins falhos, timeouts por inatividade (após 10 minutos) e restrições de sessão estão devidamente mapeados (ver detalhes em `AUDITORIA_E_TIMEOUT.md`).

## 📄 Licença

Este projeto é protegido. Consulte as diretrizes do proprietário ou a licença aplicável para distribuição ou modificação.
