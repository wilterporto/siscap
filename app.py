from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, Caixa, Aluno, User, Audit, SystemConfig, get_local_time
from config import DevelopmentConfig, ProductionConfig
from datetime import datetime, timedelta
from sqlalchemy import func, text
import os
import re
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

# Load environment variables
load_dotenv()

def validate_cpf(cpf):
    # Remove non-numeric characters
    cpf = ''.join(filter(str.isdigit, cpf))
    
    if len(cpf) != 11:
        return False
        
    # Check if all digits are equal (e.g. 111.111.111-11)
    if cpf == cpf[0] * 11:
        return False
        
    # Calculate first digit
    soma = 0
    for i in range(9):
        soma += int(cpf[i]) * (10 - i)
    resto = (soma * 10) % 11
    if resto == 10:
        resto = 0
    if resto != int(cpf[9]):
        return False
        
    # Calculate second digit
    soma = 0
    for i in range(10):
        soma += int(cpf[i]) * (11 - i)
    resto = (soma * 10) % 11
    if resto == 10:
        resto = 0
    if resto != int(cpf[10]):
        return False
        
    return True

def format_cpf(cpf):
    cpf = ''.join(filter(str.isdigit, cpf))
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"

def normalize_text(text):
    if not text:
        return text
    import unicodedata
    if not isinstance(text, str):
        text = str(text)
    # Normalize unicode characters to decomposed form (NFD)
    nfkd_form = unicodedata.normalize('NFD', text)
    # Filter out non-spacing mark characters (accents)
    only_ascii = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    # Return uppercase
    return only_ascii.upper()

# Global variable to track last cleanup time
last_cleanup_time = None

def cleanup_old_exports():
    """Remove arquivos de exportação na pasta static/downloads com mais de 5 dias"""
    global last_cleanup_time
    now = get_local_time()
    
    # Executar limpeza no máximo uma vez a cada hora para evitar overhead
    if last_cleanup_time and (now - last_cleanup_time) < timedelta(hours=1):
        return

    try:
        downloads_folder = os.path.join(app.root_path, 'static', 'downloads')
        if not os.path.exists(downloads_folder):
            return

        five_days_ago = now - timedelta(days=5)
        
        for filename in os.listdir(downloads_folder):
            file_path = os.path.join(downloads_folder, filename)
            
            # Garantir que é um arquivo (não diretório) e checar data de modificação
            if os.path.isfile(file_path):
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path)).replace(tzinfo=now.tzinfo)
                
                if file_time < five_days_ago:
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        print(f"Erro ao remover arquivo antigo {filename}: {e}")
        
        last_cleanup_time = now
    except Exception as e:
        print(f"Erro na rotina de limpeza de exportações: {e}")

def create_app(config_class=DevelopmentConfig):
    if os.environ.get('FLASK_ENV') == 'production':
        config_class = ProductionConfig

    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Configuração de timeout de sessão (10 minutos)
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=10)
    
    # Initialize extensions
    db.init_app(app)
    
    login_manager = LoginManager()
    login_manager.login_view = 'login'
    login_manager.login_message = ''
    login_manager.login_message_category = 'info'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    return app, login_manager

app, login_manager = create_app()

with app.app_context():
    db.create_all()
    # Simple migration to add column if not exists (for existing dbs)
    try:
        with db.engine.connect() as conn:
            conn.execute(text("ALTER TABLE aluno ADD COLUMN homonimo_verificado BOOLEAN DEFAULT 0"))
            conn.commit()
    except Exception:
        pass # Column likely exists

    try:
        with db.engine.connect() as conn:
            conn.execute(text("ALTER TABLE aluno ADD COLUMN nome_pai VARCHAR(100)"))
            conn.commit()
    except Exception:
        pass # Column likely exists

    try:
        with db.engine.connect() as conn:
            conn.execute(text("ALTER TABLE system_config ADD COLUMN favicon_path VARCHAR(200)"))
            conn.commit()
    except Exception:
        pass # Column likely exists

    try:
        with db.engine.connect() as conn:
            conn.execute(text("ALTER TABLE user ADD COLUMN role VARCHAR(20) DEFAULT 'Usuário'"))
            conn.commit()
    except Exception:
        pass # Column likely exists
        
    try:
        with db.engine.connect() as conn:
            conn.execute(text("ALTER TABLE system_config ADD COLUMN permitir_alunos_acima_capacidade BOOLEAN DEFAULT 0"))
            conn.commit()
    except Exception:
        pass # Column likely exists
        
    try:
        admin_user = User.query.filter_by(username='admin').first()
        if admin_user and admin_user.role != 'Administrador':
            admin_user.role = 'Administrador'
            db.session.commit()
    except Exception:
        pass
    
    # Nota: A coluna data_nascimento foi alterada para nullable=True no modelo.
    # SQLite não suporta ALTER COLUMN para modificar constraints diretamente.
    # Para bancos existentes, a coluna continuará NOT NULL até que seja recriada.
    # Novos bancos terão a coluna como nullable automaticamente via db.create_all().
    
    # Migração: Tornar nome_mae e data_nascimento nullable
    try:
        with db.engine.connect() as conn:
            # Verificar se a migração já foi aplicada
            result = conn.execute(text("SELECT sql FROM sqlite_master WHERE type='table' AND name='aluno'"))
            table_sql = result.fetchone()[0]
            
            # Se a tabela ainda tem NOT NULL em nome_mae ou data_nascimento, precisamos migrar
            if 'nome_mae VARCHAR(100) NOT NULL' in table_sql or 'data_nascimento DATE NOT NULL' in table_sql:
                print("Aplicando migração: tornando nome_mae e data_nascimento nullable...")
                
                # 1. Criar tabela temporária com estrutura correta
                conn.execute(text("""
                    CREATE TABLE aluno_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nome VARCHAR(100) NOT NULL,
                        data_nascimento DATE,
                        nome_mae VARCHAR(100),
                        nome_pai VARCHAR(100),
                        caixa_id INTEGER NOT NULL,
                        ativo BOOLEAN DEFAULT 0,
                        homonimo_verificado BOOLEAN DEFAULT 0,
                        created_by_id INTEGER,
                        FOREIGN KEY (caixa_id) REFERENCES caixa(id),
                        FOREIGN KEY (created_by_id) REFERENCES user(id)
                    )
                """))
                
                # 2. Copiar dados da tabela antiga para a nova
                conn.execute(text("""
                    INSERT INTO aluno_new (id, nome, data_nascimento, nome_mae, nome_pai, caixa_id, ativo, homonimo_verificado, created_by_id)
                    SELECT id, nome, data_nascimento, nome_mae, nome_pai, caixa_id, ativo, homonimo_verificado, created_by_id
                    FROM aluno
                """))
                
                # 3. Remover tabela antiga
                conn.execute(text("DROP TABLE aluno"))
                
                # 4. Renomear nova tabela
                conn.execute(text("ALTER TABLE aluno_new RENAME TO aluno"))
                
                conn.commit()
                print("Migração aplicada com sucesso!")
    except Exception as e:
        print(f"Erro ou migração já aplicada: {e}")
        pass



@app.context_processor
def inject_system_config():
    return dict(system_config=SystemConfig.query.first())

@app.before_request
def check_session_timeout():
    """Verifica se a sessão expirou por inatividade (10 minutos)"""
    if current_user.is_authenticated:
        session.permanent = True
        last_activity = session.get('last_activity')
        
        if last_activity:
            try:
                last_activity_time = datetime.fromisoformat(last_activity)
                now = get_local_time()
                
                # Suporte a transição suave de UTC naive para timezone aware
                if last_activity_time.tzinfo is None:
                    last_activity_time = last_activity_time.replace(tzinfo=now.tzinfo)
                
                # Se passou mais de 10 minutos desde a última atividade
                if now - last_activity_time > timedelta(minutes=10):
                    logout_user()
                    session.clear()
                    flash('Sua sessão expirou por inatividade. Por favor, faça login novamente.', 'warning')
                    return redirect(url_for('login'))
            except Exception:
                pass
        
        # Atualizar timestamp da última atividade
        session['last_activity'] = get_local_time().isoformat()
    
    # Executa a limpeza automática de arquivos temporários de exportação
    cleanup_old_exports()

@app.before_request
def check_admin_access():
    admin_routes = ['/usuarios', '/configuracoes', '/importacoes', '/auditoria', '/usuarios/gerenciar']
    if request.path in admin_routes or request.path.startswith('/usuarios/'):
        if current_user.is_authenticated and current_user.role != 'Administrador':
            flash('Acesso negado. Apenas administradores podem acessar esta área.', 'error')
            return redirect(url_for('dashboard'))

@app.cli.command("create-admin")
def create_admin():
    """Creates the initial admin user."""
    username = input("Enter admin username: ")
    cpf = input("Enter admin CPF (digits only or formatted): ")
    email = input("Enter admin email: ")
    password = input("Enter admin password: ")
    
    with app.app_context():
        if User.query.filter_by(username=username).first():
            print("User already exists!")
            return
            
        clean_cpf = ''.join(filter(str.isdigit, cpf))
        if not validate_cpf(clean_cpf):
            print("Invalid CPF!")
            return
            
        formatted_cpf = format_cpf(clean_cpf)
            
        user = User(
            username=username,
            cpf=formatted_cpf,
            email=email,
            role='Administrador'
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        db.session.add(user)
        db.session.commit()
        print(f"User {username} created successfully!")

@app.cli.command("delete-all-caixas")
def delete_all_caixas():
    """Deletes all Caixas and associated Alunos."""
    with app.app_context():
        num_caixas = Caixa.query.count()
        if num_caixas == 0:
            print("Nenhuma caixa encontrada.")
            return

        num_alunos = Aluno.query.count()
        print(f"Encontradas {num_caixas} caixas e {num_alunos} alunos.")
        
        # Confirmation (handled by arguments or assumed yes for this tool usage, 
        # but safely we delete students first)
        try:
            # Delete Alunos first (dependencies)
            deleted_alunos = Aluno.query.delete()
            # Delete Caixas
            deleted_caixas = Caixa.query.delete()
            
            db.session.commit()
            print(f"Sucesso! {deleted_caixas} caixas e {deleted_alunos} alunos foram excluídos.")
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao excluir: {str(e)}")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    config = SystemConfig.query.first()
        
    if request.method == 'POST':
        login_input = request.form.get('username') # Form field name is 'username' but accepts all
        password = request.form.get('password')
        
        # Determine if input is CPF (digits only or formatted), Email, or Username
        user = None
        
        # Normalize input if it looks like CPF
        clean_input = ''.join(filter(str.isdigit, login_input))
        
        if '@' in login_input:
            user = User.query.filter_by(email=login_input).first()
        elif len(clean_input) == 11 and validate_cpf(clean_input):
            # Try to match stored formatted CPF or raw digits depending on storage
            # We store formatted CPF in DB: 000.000.000-00
            formatted = format_cpf(clean_input)
            user = User.query.filter_by(cpf=formatted).first()
        else:
            user = User.query.filter_by(username=login_input).first()
        
        if user and user.check_password(password):
            if not user.active:
                flash('Usuário inativo via administração.', 'error')
            else:
                login_user(user)
                session.permanent = True
                session['last_activity'] = get_local_time().isoformat()
                log_audit('LOGIN', 'User', target_id=user.id, details='Login successful')
                return redirect(url_for('dashboard'))
        else:
            flash('Usuário/CPF/E-mail ou senha inválidos.', 'error')
            
    return render_template('login_v2.html', config=config)

@app.route('/recuperar-senha', methods=['GET', 'POST'])
def recuperar_senha():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            config = SystemConfig.query.first()
            if not config or not config.smtp_server:
                flash('Servidor de e-mail não configurado.', 'error')
            else:
                # In a real app, send a token link. Since we want simple recovery:
                # Generate new password
                import secrets
                import string
                import smtplib
                from email.mime.text import MIMEText
                
                alphabet = string.ascii_letters + string.digits
                new_password = ''.join(secrets.choice(alphabet) for i in range(10))
                user.set_password(new_password)
                db.session.commit()
                
                try:
                    msg = MIMEText(f'Sua nova senha é: {new_password}')
                    msg['Subject'] = 'Recuperação de Senha - SISCAP'
                    msg['From'] = config.smtp_sender_email or config.smtp_username
                    msg['To'] = email
                    
                    server = smtplib.SMTP(config.smtp_server, config.smtp_port)
                    if config.smtp_use_tls:
                        server.starttls()
                    server.login(config.smtp_username, config.smtp_password)
                    server.send_message(msg)
                    server.quit()
                    
                    flash('Uma nova senha foi enviada para seu e-mail.', 'success')
                    return redirect(url_for('login'))
                except Exception as e:
                    flash(f'Erro ao enviar e-mail: {str(e)}', 'error')
        else:
            flash('E-mail não encontrado.', 'error')
            
    return render_template('recuperar_senha.html')

@app.route('/logout')
@login_required
def logout():
    log_audit('LOGOUT', 'User', target_id=current_user.id, details='Logout successful')
    db.session.commit()
    logout_user()
    session.clear()
    return redirect(url_for('login'))

@app.route('/sobre')
@login_required
def sobre():
    return render_template('sobre.html')

# Helper function for auditing
def log_audit(action, target_type, target_id=None, details=None):
    try:
        user_id = current_user.id if current_user.is_authenticated else None
        audit = Audit(
            user_id=user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details
        )
        db.session.add(audit)
        # Commit should be handled by the caller or auto-flush to ensure consistency
    except Exception as e:
        print(f"Error logging audit: {e}")

@app.route('/meu_perfil', methods=['GET', 'POST'])
@login_required
def meu_perfil():
    if request.method == 'POST':
        user = User.query.get(current_user.id)
        
        username = request.form.get('username')
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        cpf = request.form.get('cpf')
        
        senha_atual = request.form.get('senha_atual')
        nova_senha = request.form.get('nova_senha')
        confirmar_senha = request.form.get('confirmar_senha')
        
        if senha_atual or nova_senha or confirmar_senha:
            if not user.check_password(senha_atual):
                flash('Senha atual incorreta.', 'error')
                return redirect(url_for('meu_perfil'))
            if nova_senha != confirmar_senha:
                flash('As novas senhas não conferem.', 'error')
                return redirect(url_for('meu_perfil'))
            if not nova_senha:
                flash('A nova senha não pode ser vazia.', 'error')
                return redirect(url_for('meu_perfil'))
            user.set_password(nova_senha)

        if username and username != user.username:
            if User.query.filter_by(username=username).first():
                flash('Nome de usuário já existe!', 'error')
                return redirect(url_for('meu_perfil'))
            user.username = username
            
        if email and email != user.email:
            if User.query.filter_by(email=email).first():
                flash('E-mail já cadastrado!', 'error')
                return redirect(url_for('meu_perfil'))
            user.email = email
            
        if cpf and cpf != user.cpf:
            if not validate_cpf(cpf):
                flash('CPF inválido!', 'error')
                return redirect(url_for('meu_perfil'))
            formatted_cpf = format_cpf(cpf)
            if User.query.filter_by(cpf=formatted_cpf).first():
                flash('CPF já cadastrado!', 'error')
                return redirect(url_for('meu_perfil'))
            user.cpf = formatted_cpf
            
        user.full_name = full_name
        
        log_audit('UPDATE', 'Perfil', target_id=user.id, details=f'Perfil atualizado pelo próprio usuário.')
        db.session.commit()
        flash('Perfil atualizado com sucesso!', 'success')
        return redirect(url_for('meu_perfil'))
        
    return render_template('meu_perfil.html')

@app.route('/usuarios', methods=['GET'])
@login_required
def listar_usuarios():
    users = User.query.all()
    return render_template('usuarios.html', users=users)

@app.route('/usuarios/gerenciar', methods=['POST'])
@login_required
def gerenciar_usuario():
    action = request.form.get('action')
    user_id = request.form.get('user_id')
    
    if action == 'create':
        username = request.form.get('username')
        password = request.form.get('password')
        cpf = request.form.get('cpf')
        email = request.form.get('email')
        
        # Validation
        if not validate_cpf(cpf):
            flash('CPF inválido!', 'error')
            return redirect(url_for('listar_usuarios'))
            
        formatted_cpf = format_cpf(cpf)
            
        if User.query.filter_by(username=username).first():
            flash('Usuário já existe!', 'error')
        elif User.query.filter_by(cpf=formatted_cpf).first():
            flash('CPF já cadastrado!', 'error')
        elif User.query.filter_by(email=email).first():
            flash('E-mail já cadastrado!', 'error')
        else:
            active = True if request.form.get('active') == 'on' else False
            role = request.form.get('role', 'Usuário')
            user = User(
                username=username,
                cpf=formatted_cpf,
                email=email,
                role=role,
                active=active
            )
            user.set_password(password)
            db.session.add(user)
            log_audit('CREATE', 'User', details=f'Username: {username}, CPF: {formatted_cpf}, Active: {active}')
            db.session.commit()
            flash('Usuário criado com sucesso!', 'success')
            
    elif action == 'edit':
        user = User.query.get(user_id)
        if user:
            username = request.form.get('username')
            email = request.form.get('email')
            
            # Check unique constraints if changed
            if username and username != user.username:
                if User.query.filter_by(username=username).first():
                    flash('Nome de usuário já existe!', 'error')
                    return redirect(url_for('listar_usuarios'))
                user.username = username
                
            if email and email != user.email:
                if User.query.filter_by(email=email).first():
                    flash('E-mail já cadastrado!', 'error')
                    return redirect(url_for('listar_usuarios'))
                user.email = email

            # Update Active Status and Role
            if user.id != current_user.id:
                active_req = True if request.form.get('active') == 'on' else False
                new_role = request.form.get('role')
                
                # Check 1: admin profile can't be changed
                if user.username == 'admin':
                    new_role = 'Administrador'

                # Check 2: Decreasing Administrador active users
                if user.role == 'Administrador' and user.active:
                    if not active_req or (new_role and new_role != 'Administrador'):
                        active_admins = User.query.filter_by(role='Administrador', active=True).count()
                        if active_admins <= 1:
                            flash('Não é possível inativar ou alterar o perfil do último administrador ativo do sistema.', 'error')
                            return redirect(url_for('listar_usuarios'))

                user.active = active_req
                if new_role:
                    user.role = new_role
            
            new_password = request.form.get('password')
            if new_password:
                user.set_password(new_password)
                
            log_audit('UPDATE', 'User', target_id=user.id, details=f'Updated user {user.username}')
            db.session.commit()
            flash('Usuário atualizado com sucesso!', 'success')
            
    elif action == 'toggle_status':
        user = User.query.get(user_id)
        if user:
            if user.id == current_user.id:
                 flash('Você não pode inativar a si mesmo!', 'error')
            else:
                if user.role == 'Administrador' and user.active:
                    active_admins = User.query.filter_by(role='Administrador', active=True).count()
                    if active_admins <= 1:
                        flash('Não é possível inativar o último administrador ativo do sistema.', 'error')
                        return redirect(url_for('listar_usuarios'))
                        
                user.active = not user.active
                db.session.add(user)
                log_audit('UPDATE', 'User', target_id=user.id, details=f'Status changed to {user.active}')
                db.session.commit()
                flash(f'Usuário {"ativado" if user.active else "inativado"} com sucesso!', 'success')

    elif action == 'delete':
        user = User.query.get(user_id)
        if user:
            if user.id == current_user.id:
                 flash('Você não pode excluir a si mesmo!', 'error')
            else:
                if user.username == 'admin':
                    flash('O usuário admin não pode ser excluído.', 'error')
                    return redirect(url_for('listar_usuarios'))
                
                if user.role == 'Administrador' and user.active:
                    active_admins = User.query.filter_by(role='Administrador', active=True).count()
                    if active_admins <= 1:
                        flash('Não é possível excluir o último administrador ativo do sistema.', 'error')
                        return redirect(url_for('listar_usuarios'))

                # Check constraints
                has_students = Aluno.query.filter_by(created_by_id=user.id).first()
                has_audits = Audit.query.filter_by(user_id=user.id).first()
                
                if has_students or has_audits:
                    flash('Não é possível excluir usuário com registros associados (alunos ou auditoria). Inative-o em vez disso.', 'error')
                else:
                    db.session.delete(user)
                    log_audit('DELETE', 'User', target_id=user.id, details=f'Username: {user.username}')
                    db.session.commit()
                    flash('Usuário excluído com sucesso!', 'success')

    return redirect(url_for('listar_usuarios'))

@app.route('/configuracoes', methods=['GET', 'POST'])
@login_required
def configuracoes():
    config = SystemConfig.query.first()
    if not config:
        config = SystemConfig()
        db.session.add(config)
        db.session.commit()
        
    if request.method == 'POST':
        config.smtp_server = request.form.get('smtp_server')
        config.smtp_port = int(request.form.get('smtp_port', 587))
        config.smtp_username = request.form.get('smtp_username')
        config.smtp_password = request.form.get('smtp_password') # In real app, encrypt this
        config.smtp_use_tls = True if request.form.get('smtp_use_tls') == 'on' else False
        config.smtp_sender_email = request.form.get('smtp_sender_email')
        config.permitir_alunos_acima_capacidade = True if request.form.get('permitir_alunos_acima_capacidade') == 'on' else False
        
        # Handle Image Upload
        if 'login_image' in request.files:
            file = request.files['login_image']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                # Create upload folder if not exists
                upload_folder = os.path.join(app.root_path, 'static', 'uploads')
                if not os.path.exists(upload_folder):
                    os.makedirs(upload_folder)
                    
                filepath = os.path.join(upload_folder, filename)
                file.save(filepath)
                config.login_image = f'uploads/{filename}'
        
        # Handle Favicon Upload
        if 'favicon' in request.files:
            file = request.files['favicon']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                # Create upload folder if not exists
                upload_folder = os.path.join(app.root_path, 'static', 'uploads')
                if not os.path.exists(upload_folder):
                    os.makedirs(upload_folder)
                    
                filepath = os.path.join(upload_folder, filename)
                file.save(filepath)
                
                try:
                    from PIL import Image
                    img = Image.open(filepath)
                    
                    # Redimensiona mantendo a proporção (máximo 512x512)
                    img.thumbnail((512, 512), Image.Resampling.LANCZOS)
                    
                    ext = filename.lower()
                    if ext.endswith('.png'):
                        img.save(filepath, format="PNG", optimize=True)
                    elif ext.endswith(('.jpg', '.jpeg')):
                        if img.mode in ("RGBA", "P"):
                            img = img.convert("RGB")
                        img.save(filepath, format="JPEG", optimize=True, quality=85)
                    elif ext.endswith('.ico'):
                        img.save(filepath, format="ICO")
                    else:
                        img.save(filepath, optimize=True)
                except ImportError:
                    print("Atenção: A biblioteca Pillow não está instalada. A compressão de imagem foi pulada.")
                except Exception as e:
                    print(f"Erro ao comprimir favicon: {str(e)}")
                    
                config.favicon_path = f'uploads/{filename}'
        
        db.session.commit()
        flash('Configurações salvas com sucesso!', 'success')
        return redirect(url_for('configuracoes'))
        
    return render_template('configuracoes.html', config=config)

@app.route('/')
@login_required
def dashboard():
    # Count students per letter (for existing chart)
    data = db.session.query(Caixa.letra, func.count(Aluno.id)).outerjoin(Aluno).group_by(Caixa.letra).all()
    labels = [item[0] for item in data]
    values = [item[1] for item in data]
    
    # Homonyms Stats
    # Get names that appear more than once
    homonym_names = [r[0] for r in db.session.query(Aluno.nome).group_by(Aluno.nome).having(func.count(Aluno.nome) > 1).all()]
    
    if homonym_names:
        homonimos_query = Aluno.query.filter(Aluno.nome.in_(homonym_names))
    else:
        homonimos_query = Aluno.query.filter(text("1=0")) # Empty result
    
    total_homonimos = homonimos_query.count()
    nao_verificados = homonimos_query.filter(Aluno.homonimo_verificado == False).count()
    
    # Homonyms per letter
    if homonym_names:
        homonimos_por_letra = db.session.query(
            func.substr(Aluno.nome, 1, 1).label('letra'), 
            func.count(Aluno.id)
        ).filter(Aluno.nome.in_(homonym_names))\
         .group_by('letra')\
         .order_by('letra').all()
         
        h_labels = [h[0] for h in homonimos_por_letra]
        h_values = [h[1] for h in homonimos_por_letra]
    else:
        h_labels = []
        h_values = []

    # Siblings Stats (Same Mother Name, Different Student Name)
    # Get mother names with > 1 student associated
    mae_names = [r[0] for r in db.session.query(Aluno.nome_mae).filter(Aluno.nome_mae.isnot(None), Aluno.nome_mae != '').group_by(Aluno.nome_mae).having(func.count(Aluno.id) > 1).all()]
    
    # Get all students with these mothers
    if mae_names:
        potential_siblings = Aluno.query.filter(Aluno.nome_mae.in_(mae_names)).all()
    else:
        potential_siblings = []
    
    # Group by mother and filter out homonyms (same student name) within the group
    siblings_map = {}
    for aluno in potential_siblings:
        if aluno.nome_mae not in siblings_map:
            siblings_map[aluno.nome_mae] = []
        siblings_map[aluno.nome_mae].append(aluno.nome)
        
    total_irmaos = 0
    for mae, nomes in siblings_map.items():
        # Only count if there are at least 2 DISTINCT names
        if len(set(nomes)) > 1:
            total_irmaos += len(nomes)
    
    total_caixas = Caixa.query.count()
    
    # Caixas acima da capacidade (> 100 alunos)
    caixas_acima_capacidade = db.session.query(Caixa.id)\
        .join(Aluno, Aluno.caixa_id == Caixa.id)\
        .group_by(Caixa.id)\
        .having(func.count(Aluno.id) > 100)\
        .count()

    total_ativos = Aluno.query.filter_by(ativo=True).count()

    return render_template('dashboard.html', 
                           labels=labels, values=values,
                           total_homonimos=total_homonimos,
                           nao_verificados=nao_verificados,
                           h_labels=h_labels, h_values=h_values,
                           total_irmaos=total_irmaos,
                           total_caixas=total_caixas,
                           caixas_acima_capacidade=caixas_acima_capacidade,
                           total_ativos=total_ativos)

@app.route('/caixas', methods=['GET', 'POST'])
@login_required
def caixas():
    if request.method == 'POST':
        letra = request.form.get('letra').upper()
        numero = request.form.get('numero')
        
        existing = Caixa.query.filter_by(letra=letra, numero=numero).first()
        if existing:
            flash('Caixa já existe!', 'error')
        else:
            nova_caixa = Caixa(letra=letra, numero=numero)
            db.session.add(nova_caixa)
            db.session.commit()
            flash('Caixa cadastrada com sucesso!', 'success')
        return redirect(url_for('caixas'))

    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    acima_capacidade = request.args.get('acima_capacidade', '', type=str)

    query = db.session.query(Caixa, func.count(Aluno.id))\
        .outerjoin(Aluno, Aluno.caixa_id == Caixa.id)\
        .group_by(Caixa.id)
    
    if search:
        query = query.filter(
            (Caixa.letra.ilike(f'%{search}%')) | 
            (func.cast(Caixa.numero, db.String).ilike(f'%{search}%'))
        )
    
    # Filtro para caixas acima da capacidade
    if acima_capacidade == 'true':
        query = query.having(func.count(Aluno.id) > 100)

    pagination = query.order_by(Caixa.letra, Caixa.numero).paginate(page=page, per_page=30)
    
    return render_template('caixas.html', pagination=pagination, search=search, acima_capacidade=acima_capacidade)

@app.route('/caixas/editar/<int:id>', methods=['POST'])
@login_required
def edit_caixa(id):
    caixa = Caixa.query.get_or_404(id)
    letra = request.form.get('letra').upper()
    numero = request.form.get('numero')
    
    # Check for duplicates excluding self
    existing = Caixa.query.filter(Caixa.letra == letra, Caixa.numero == numero, Caixa.id != id).first()
    if existing:
        flash('Já existe outra caixa com esta letra e número!', 'error')
    else:
        caixa.letra = letra
        caixa.numero = numero
        log_audit('UPDATE', 'Caixa', target_id=caixa.id, details=f'{caixa.nome_formatado}')
        db.session.commit()
        flash('Caixa atualizada com sucesso!', 'success')
        
    return redirect(url_for('caixas'))

@app.route('/caixas/excluir/<int:id>', methods=['POST'])
@login_required
def delete_caixa(id):
    caixa = Caixa.query.get_or_404(id)
    
    # Check if has students
    count = Aluno.query.filter_by(caixa_id=id).count()
    if count > 0:
        flash(f'Não é possível excluir a caixa {caixa.nome_formatado} pois ela contém {count} alunos.', 'error')
    else:
        db.session.delete(caixa)
        log_audit('DELETE', 'Caixa', target_id=id, details=f'{caixa.nome_formatado}')
        db.session.commit()
        flash('Caixa excluída com sucesso!', 'success')
        
    return redirect(url_for('caixas'))

@app.route('/alunos/importar', methods=['GET'])
@login_required
def importar_alunos():
    return render_template('importar_alunos.html')

@app.route('/alunos/importar/processar', methods=['POST'])
@login_required
def processar_importacao():
    import pandas as pd
    import time
    from flask import stream_with_context
    
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Arquivo inválido'}), 400
        
    try:
        # Load excel
        df = pd.read_excel(file)
        
        # Verify columns
        required_cols = ['Nome', 'DataNascimento', 'NomeMae', 'CaixaLetra', 'CaixaNumero']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            return jsonify({'error': f'Colunas faltando: {", ".join(missing_cols)}'}), 400
        
        total_rows = len(df)
        
        # Capture user ID outside generator to avoid context issues if strictly needed, 
        # though stream_with_context handles it.
        user_id = current_user.id
        
        def generate():
            import json
            import os
            processed_count = 0
            success_count = 0
            errors = []
            
            # Create timestamp for logs
            timestamp = get_local_time().strftime("%Y%m%d_%H%M%S")
            log_filename = f"import_errors_{user_id}_{timestamp}.txt"
            upload_folder = os.path.join(app.root_path, 'static', 'uploads')
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
            log_path = os.path.join(upload_folder, log_filename)
            
            with app.app_context():
                # --- STAGE 1: CAIXAS ---
                yield json.dumps({"status": "info", "message": "Etapa 1/2: Verificando caixas..."}) + '\n'
                
                try:
                    # Fetch all existing caixas to memory map: {(letra, numero): id}
                    existing_caixas = Caixa.query.all()
                    caixa_map = {(c.letra, c.numero): c.id for c in existing_caixas}
                    
                    # Identify needed caixas from DF
                    needed_caixas = set()
                    
                    # First pass to find caixas
                    for _, row in df.iterrows():
                        try:
                            l = normalize_text(str(row['CaixaLetra'])).strip()
                            raw_n = row['CaixaNumero']
                            try:
                                n = int(float(raw_n))
                            except:
                                n = int(raw_n)
                            # Only add if valid
                            needed_caixas.add((l, n))
                        except:
                            pass # Validation happens in stage 2
                    
                    new_caixas_list = []
                    for (l, n) in needed_caixas:
                        if (l, n) not in caixa_map:
                            new_caixas_list.append(Caixa(letra=l, numero=n))
                    
                    if new_caixas_list:
                        count_new = len(new_caixas_list)
                        yield json.dumps({"status": "info", "message": f"Etapa 1/2: Cadastrando {count_new} novas caixas..."}) + '\n'
                        db.session.bulk_save_objects(new_caixas_list)
                        db.session.commit()
                        
                        # Refresh map to get IDs of new caixas
                        existing_caixas = Caixa.query.all()
                        caixa_map = {(c.letra, c.numero): c.id for c in existing_caixas}
                    else:
                        yield json.dumps({"status": "info", "message": "Etapa 1/2: Caixas verificadas."}) + '\n'

                except Exception as e:
                     yield json.dumps({"status": "info", "message": f"Erro na verificação de caixas: {str(e)}"}) + '\n'

                # --- STAGE 2: ALUNOS ---
                yield json.dumps({"status": "start", "total": total_rows, "message": "Etapa 2/2: Importando alunos..."}) + '\n'
                
                alunos_batch = []
                BATCH_SIZE = 1000
                
                for idx, row in df.iterrows():
                    processed_count += 1
                    try:
                        nome = normalize_text(str(row['Nome'])).strip()
                        
                        # Data de nascimento é opcional
                        data_nascimento = None
                        if pd.notna(row['DataNascimento']) and str(row['DataNascimento']).strip():
                            nasc_str = str(row['DataNascimento'])
                            try:
                                if isinstance(row['DataNascimento'], (datetime, pd.Timestamp)):
                                    data_nascimento = row['DataNascimento'].date()
                                else:
                                    dt = pd.to_datetime(row['DataNascimento'], errors='coerce', dayfirst=True)
                                    if pd.notna(dt):
                                        data_nascimento = dt.date()
                            except:
                                try:
                                    data_nascimento = datetime.strptime(nasc_str, '%d/%m/%Y').date()
                                except:
                                    try:
                                        data_nascimento = datetime.strptime(nasc_str, '%Y-%m-%d').date()
                                    except:
                                        # Se não conseguir parsear, deixa None (opcional)
                                        pass
                                
                        nome_mae = normalize_text(str(row['NomeMae'])).strip() if pd.notna(row['NomeMae']) else None
                        
                        letra = normalize_text(str(row['CaixaLetra'])).strip()
                        try:
                            numero = int(float(row['CaixaNumero']))
                        except:
                            numero = int(row['CaixaNumero'])
                        
                        caixa_id = caixa_map.get((letra, numero))
                        if not caixa_id:
                            # Should exist after stage 1
                            raise ValueError(f"Caixa {letra}-{numero} não encontrada.")
                        
                        aluno = Aluno(
                            nome=nome,
                            data_nascimento=data_nascimento,
                            nome_mae=nome_mae,
                            caixa_id=caixa_id,
                            created_by_id=user_id,
                            ativo=False
                        )
                        alunos_batch.append(aluno)
                        
                        if len(alunos_batch) >= BATCH_SIZE:
                            db.session.bulk_save_objects(alunos_batch)
                            db.session.commit()
                            success_count += len(alunos_batch)
                            alunos_batch = []
                            
                    except Exception as e:
                        errors.append(f"Linha {idx + 2}: {str(e)}")
                    
                    if processed_count % 50 == 0 or processed_count == total_rows:
                        progress = int((processed_count / total_rows) * 100)
                        yield json.dumps({"status": "progress", "percent": progress, "processed": processed_count, "total": total_rows}) + '\n'
                
                if alunos_batch:
                    try:
                        db.session.bulk_save_objects(alunos_batch)
                        db.session.commit()
                        success_count += len(alunos_batch)
                    except Exception as e:
                        errors.append(f"Erro ao salvar lote final: {str(e)}")
                    
                error_url = None
                if errors:
                    try:
                        with open(log_path, 'w', encoding='utf-8') as f:
                            f.write(f"Relatório de Erros - Importação de Alunos - {timestamp}\n")
                            f.write("="*80 + "\n\n")
                            for err in errors:
                                f.write(f"{err}\n")
                        error_url = url_for('static', filename=f'uploads/{log_filename}')
                    except Exception as e:
                       errors.append(f"Falha ao gerar arquivo de log: {str(e)}")

                yield json.dumps({"status": "complete", "success": success_count, "errors": len(errors), "error_log_url": error_url}) + '\n'

        return app.response_class(stream_with_context(generate()), mimetype='application/json')

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/alunos', methods=['GET'])
@login_required
def alunos():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    caixa_id = request.args.get('caixa_id', type=int)
    sem_mae = request.args.get('sem_mae') == 'on'
    sem_data = request.args.get('sem_data') == 'on'
    somente_ativos = request.args.get('somente_ativos') == 'on'
    
    query = Aluno.query
    if search:
        query = query.filter((Aluno.nome.ilike(f'%{search}%')) | (Aluno.nome_mae.ilike(f'%{search}%')))
        
    if caixa_id:
        query = query.filter(Aluno.caixa_id == caixa_id)
        
    if sem_mae:
        query = query.filter((Aluno.nome_mae == None) | (Aluno.nome_mae == ''))
        
    if sem_data:
        query = query.filter(Aluno.data_nascimento == None)
        
    if somente_ativos:
        query = query.filter(Aluno.ativo == True)
        
    pagination = query.order_by(Aluno.nome).paginate(page=page, per_page=30)
    
    caixas_records = db.session.query(Caixa, func.count(Aluno.id)).outerjoin(Aluno, Aluno.caixa_id == Caixa.id).group_by(Caixa.id).order_by(Caixa.letra, Caixa.numero).all()
    caixas_info = [{'id': c.id, 'nome_formatado': c.nome_formatado, 'count': count} for c, count in caixas_records]
    
    system_config = SystemConfig.query.first()
    permitir_acima = system_config.permitir_alunos_acima_capacidade if system_config else False
    
    return render_template('alunos.html', pagination=pagination, search=search, caixa_id=caixa_id, sem_mae=sem_mae, sem_data=sem_data, somente_ativos=somente_ativos, caixas=caixas_info, permitir_acima=permitir_acima)

@app.route('/alunos/novo', methods=['GET', 'POST'])
@login_required
def novo_aluno():
    if request.method == 'POST':
        nome = normalize_text(request.form.get('nome'))
        
        # Data de nascimento é opcional
        data_nascimento = None
        data_nascimento_input = request.form.get('data_nascimento')
        
        if data_nascimento_input:  # Se foi fornecida uma data
            try:
                data_nascimento = datetime.strptime(data_nascimento_input, '%Y-%m-%d').date()
                today = get_local_time().date()
                
                if data_nascimento > today:
                    flash('A data de nascimento não pode estar no futuro.', 'error')
                    return redirect(url_for('novo_aluno'))
                elif data_nascimento.year < 1900:
                    flash('O ano de nascimento não pode ser menor que 1900.', 'error')
                    return redirect(url_for('novo_aluno'))
            except ValueError:
                flash('Data de nascimento inválida.', 'error')
                return redirect(url_for('novo_aluno'))

        nome_mae = request.form.get('nome_mae')
        nome_mae = normalize_text(nome_mae) if nome_mae and nome_mae.strip() else None
        
        nome_pai = request.form.get('nome_pai')
        nome_pai = normalize_text(nome_pai) if nome_pai and nome_pai.strip() else None
            
        caixa_id = request.form.get('caixa_id')
        ativo = True if request.form.get('ativo') == 'on' else False
        
        caixa = Caixa.query.get(caixa_id)
        if not caixa:
            flash('Caixa inválida selecionada.', 'error')
            return redirect(url_for('novo_aluno'))
            
        system_config = SystemConfig.query.first()
        permitir_acima = system_config.permitir_alunos_acima_capacidade if system_config else False
        current_count = Aluno.query.filter_by(caixa_id=caixa.id).count()
        
        if current_count >= 100 and not permitir_acima:
            flash(f'A caixa {caixa.nome_formatado} já está cheia (100 alunos). Para adicionar alunos além da capacidade, altere a configuração do sistema.', 'error')
        else:
            nov = Aluno(
                nome=nome, 
                data_nascimento=data_nascimento, 
                nome_mae=nome_mae, 
                nome_pai=nome_pai,
                caixa_id=caixa_id,
                ativo=ativo,
                homonimo_verificado=True if request.form.get('homonimo_verificado') == 'on' else False,
                created_by_id=current_user.id
            )
            db.session.add(nov)
            log_audit('CREATE', 'Aluno', details=f'Nome: {nome}, Caixa: {caixa.nome_formatado}')
            db.session.commit()
            flash('Aluno cadastrado com sucesso!', 'success')
            return redirect(url_for('alunos'))
            
    system_config = SystemConfig.query.first()
    permitir_acima = system_config.permitir_alunos_acima_capacidade if system_config else False
    
    caixas_records = db.session.query(Caixa, func.count(Aluno.id)).outerjoin(Aluno, Aluno.caixa_id == Caixa.id).group_by(Caixa.id).order_by(Caixa.letra, Caixa.numero).all()
    caixas_info = [{'id': c.id, 'nome_formatado': c.nome_formatado, 'count': count} for c, count in caixas_records]
    
    return render_template('novo_aluno.html', caixas=caixas_info, permitir_acima=permitir_acima)

@app.route('/alunos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_aluno(id):
    aluno = Aluno.query.get_or_404(id)
    
    
    if request.method == 'POST':
        nome = normalize_text(request.form.get('nome'))
        
        # Data de nascimento é opcional
        data_nascimento = None
        data_nascimento_input = request.form.get('data_nascimento')
        
        if data_nascimento_input:  # Se foi fornecida uma data
            try:
                data_nascimento = datetime.strptime(data_nascimento_input, '%Y-%m-%d').date()
                today = get_local_time().date()
                
                if data_nascimento > today:
                    flash('A data de nascimento não pode estar no futuro.', 'error')
                    return redirect(url_for('alunos'))
                elif data_nascimento.year < 1900:
                    flash('O ano de nascimento não pode ser menor que 1900.', 'error')
                    return redirect(url_for('alunos'))
            except ValueError:
                flash('Data de nascimento inválida.', 'error')
                return redirect(url_for('alunos'))

        nome_mae = request.form.get('nome_mae')
        nome_mae = normalize_text(nome_mae) if nome_mae and nome_mae.strip() else None
        
        nome_pai = request.form.get('nome_pai')
        nome_pai = normalize_text(nome_pai) if nome_pai and nome_pai.strip() else None
            
        caixa_id = request.form.get('caixa_id')
        ativo = True if request.form.get('ativo') == 'on' else False
        
        caixa = Caixa.query.get(caixa_id)
        if not caixa:
            flash('Caixa inválida selecionada.', 'error')
        else:
            # Check capacity only if changing boxes
            if int(caixa_id) != aluno.caixa_id:
                system_config = SystemConfig.query.first()
                permitir_acima = system_config.permitir_alunos_acima_capacidade if system_config else False
                current_count = Aluno.query.filter_by(caixa_id=caixa.id).count()
                if current_count >= 100 and not permitir_acima:
                    flash(f'A caixa {caixa.nome_formatado} já está cheia (100 alunos). Para adicionar alunos além da capacidade, altere a configuração do sistema.', 'error')
                    return redirect(url_for('alunos'))

            aluno.nome = nome
            aluno.data_nascimento = data_nascimento
            aluno.nome_mae = nome_mae
            aluno.nome_pai = nome_pai
            aluno.caixa_id = caixa_id
            aluno.ativo = ativo
            aluno.homonimo_verificado = True if request.form.get('homonimo_verificado') == 'on' else False
            
            log_audit('UPDATE', 'Aluno', target_id=aluno.id, details=f'Nome: {nome}, Caixa: {caixa.nome_formatado}')
            db.session.commit()
            flash('Aluno atualizado com sucesso!', 'success')
            return redirect(url_for('alunos'))
            
    system_config = SystemConfig.query.first()
    permitir_acima = system_config.permitir_alunos_acima_capacidade if system_config else False
    caixas_records = db.session.query(Caixa, func.count(Aluno.id)).outerjoin(Aluno, Aluno.caixa_id == Caixa.id).group_by(Caixa.id).order_by(Caixa.letra, Caixa.numero).all()
    caixas_info = [{'id': c.id, 'nome_formatado': c.nome_formatado, 'count': count} for c, count in caixas_records]
    return render_template('novo_aluno.html', caixas=caixas_info, aluno=aluno, permitir_acima=permitir_acima)

@app.route('/alunos/excluir/<int:id>', methods=['POST'])
@login_required
def delete_aluno(id):
    aluno = Aluno.query.get_or_404(id)
    nome = aluno.nome
    db.session.delete(aluno)
    log_audit('DELETE', 'Aluno', target_id=id, details=f'Nome: {nome}')
    db.session.commit()
    flash('Aluno excluído com sucesso!', 'success')
    return redirect(url_for('alunos'))


@app.route('/api/sugerir-caixa')
@login_required
def sugerir_caixa():
    nome_aluno = request.args.get('nome', '')
    if not nome_aluno:
        return jsonify({'caixa_id': None, 'mensagem': 'Nome vazio'})
        
    initial = nome_aluno[0].upper()
    
    candidates = Caixa.query.filter_by(letra=initial).order_by(Caixa.numero).all()
    
    selected_caixa = None
    
    for caixa in candidates:
        count = Aluno.query.filter_by(caixa_id=caixa.id).count()
        if count < 100:
            selected_caixa = caixa
            break
            
    if selected_caixa:
        return jsonify({
            'caixa_id': selected_caixa.id,
            'caixa_nome': selected_caixa.nome_formatado,
            'mensagem': f'Caixa sugerida: {selected_caixa.nome_formatado}'
        })
    else:
        return jsonify({'caixa_id': None, 'mensagem': f'Nenhuma caixa com a letra {initial} disponível com vagas.'})

@app.route('/homonimos')
@login_required
def homonimos():
    subquery = db.session.query(Aluno.nome).group_by(Aluno.nome).having(func.count(Aluno.nome) > 1).subquery()
    homonimos = Aluno.query.filter(Aluno.nome.in_(subquery)).order_by(Aluno.nome).all()
    
    return render_template('homonimos.html', homonimos=homonimos)

@app.route('/homonimos/verificar/<int:id>')
@login_required
def verificar_homonimo(id):
    aluno = Aluno.query.get_or_404(id)
    aluno.homonimo_verificado = not aluno.homonimo_verificado
    db.session.commit()
    return redirect(url_for('homonimos'))

@app.route('/irmaos')
@login_required
def irmaos():
    # Find mothers with more than 1 child
    subquery = db.session.query(Aluno.nome_mae)\
        .filter(Aluno.nome_mae.isnot(None), Aluno.nome_mae != '')\
        .group_by(Aluno.nome_mae)\
        .having(func.count(Aluno.id) > 1)\
        .scalar_subquery()
        
    # Get all potential siblings
    candidates = Aluno.query.filter(Aluno.nome_mae.in_(subquery)).order_by(Aluno.nome_mae, Aluno.nome).all()
    
    # Group by mother
    grouped = {}
    for c in candidates:
        if c.nome_mae not in grouped:
            grouped[c.nome_mae] = []
        grouped[c.nome_mae].append(c)
        
    # Filter groups where all children have the same name (homonyms only, not siblings)
    # We want groups where there are at least 2 distinct names
    irmaos_list = []
    for mae, alunos in grouped.items():
        distinct_names = set(a.nome for a in alunos)
        if len(distinct_names) > 1:
            irmaos_list.append((mae, alunos))
            
    return render_template('irmaos.html', irmaos=irmaos_list)

@app.route('/importacoes')
@login_required
def importacoes():
    """Lista todos os arquivos de log de importação"""
    upload_folder = os.path.join(app.root_path, 'static', 'uploads')
    
    if not os.path.exists(upload_folder):
        arquivos = []
    else:
        # Listar apenas arquivos de log de importação
        all_files = os.listdir(upload_folder)
        arquivos = []
        
        for filename in all_files:
            if filename.startswith('import_errors_') and filename.endswith('.txt'):
                filepath = os.path.join(upload_folder, filename)
                file_stat = os.stat(filepath)
                
                # Extrair informações do nome do arquivo: import_errors_{user_id}_{timestamp}.txt
                parts = filename.replace('import_errors_', '').replace('.txt', '').split('_')
                
                if len(parts) >= 2:
                    user_id = parts[0]
                    timestamp_str = '_'.join(parts[1:])
                    
                    # Converter timestamp para formato legível
                    timestamp = get_local_time()  # Default
                    try:
                        timestamp = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                        data_formatada = timestamp.strftime('%d/%m/%Y %H:%M:%S')
                    except:
                        data_formatada = timestamp_str
                    
                    # Buscar nome do usuário
                    user = User.query.get(user_id)
                    username = user.username if user else f'Usuário #{user_id}'
                    
                    # Tamanho do arquivo em KB ou MB
                    size_bytes = file_stat.st_size
                    if size_bytes < 1024 * 1024:
                        size_str = f"{size_bytes / 1024:.1f} KB"
                    else:
                        size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
                    
                    arquivos.append({
                        'filename': filename,
                        'username': username,
                        'data': data_formatada,
                        'tamanho': size_str,
                        'timestamp': timestamp
                    })
        
        # Ordenar por data (mais recente primeiro)
        arquivos.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return render_template('importacoes.html', arquivos=arquivos)

@app.route('/importacoes/download/<filename>')
@login_required
def download_importacao(filename):
    """Faz o download de um arquivo de log de importação"""
    # Validar que o arquivo é um log de importação
    if not filename.startswith('import_errors_') or not filename.endswith('.txt'):
        flash('Arquivo inválido!', 'error')
        return redirect(url_for('importacoes'))
    
    upload_folder = os.path.join(app.root_path, 'static', 'uploads')
    filepath = os.path.join(upload_folder, filename)
    
    if not os.path.exists(filepath):
        flash('Arquivo não encontrado!', 'error')
        return redirect(url_for('importacoes'))
    
    from flask import send_file
    return send_file(filepath, as_attachment=True, download_name=filename)

@app.route('/importacoes/excluir/<filename>', methods=['POST'])
@login_required
def excluir_importacao(filename):
    """Exclui um arquivo de log de importação"""
    # Validar que o arquivo é um log de importação
    if not filename.startswith('import_errors_') or not filename.endswith('.txt'):
        flash('Arquivo inválido!', 'error')
        return redirect(url_for('importacoes'))
    
    upload_folder = os.path.join(app.root_path, 'static', 'uploads')
    filepath = os.path.join(upload_folder, filename)
    
    if not os.path.exists(filepath):
        flash('Arquivo não encontrado!', 'error')
        return redirect(url_for('importacoes'))
    
    try:
        os.remove(filepath)
        log_audit('DELETE', 'ImportLog', details=f'Arquivo: {filename}')
        db.session.commit()
        flash('Arquivo excluído com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao excluir arquivo: {str(e)}', 'error')
    
    return redirect(url_for('importacoes'))

@app.route('/auditoria')
@login_required
def auditoria():
    """Lista todos os registros de auditoria com filtros e paginação"""
    page = request.args.get('page', 1, type=int)
    user_filter = request.args.get('user', '', type=str)
    action_filter = request.args.get('action', '', type=str)
    target_type_filter = request.args.get('target_type', '', type=str)
    date_from = request.args.get('date_from', '', type=str)
    date_to = request.args.get('date_to', '', type=str)
    
    # Query base
    query = Audit.query
    
    # Aplicar filtros
    if user_filter:
        query = query.filter(Audit.user_id == user_filter)
    
    if action_filter:
        query = query.filter(Audit.action == action_filter)
    
    if target_type_filter:
        query = query.filter(Audit.target_type == target_type_filter)
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(Audit.timestamp >= date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            # Adicionar 1 dia para incluir todo o dia selecionado
            date_to_obj = date_to_obj + timedelta(days=1)
            query = query.filter(Audit.timestamp < date_to_obj)
        except ValueError:
            pass
    
    # Ordenar por mais recente primeiro
    query = query.order_by(Audit.timestamp.desc())
    
    # Paginação
    pagination = query.paginate(page=page, per_page=30)
    
    # Buscar lista de usuários para o filtro
    users = User.query.order_by(User.username).all()
    
    # Dicionários de tradução
    action_translations = {
        'LOGIN': 'Login',
        'LOGOUT': 'Logout',
        'CREATE': 'Criar',
        'UPDATE': 'Atualizar',
        'DELETE': 'Excluir',
        'EXPORT': 'Exportar'
    }
    
    target_type_translations = {
        'User': 'Usuário',
        'Aluno': 'Aluno',
        'Caixa': 'Caixa',
        'ImportLog': 'Log de Importação'
    }
    
    # Lista de ações disponíveis (chave interna, valor exibido)
    actions = [
        {'value': 'LOGIN', 'label': 'Login'},
        {'value': 'LOGOUT', 'label': 'Logout'},
        {'value': 'CREATE', 'label': 'Criar'},
        {'value': 'UPDATE', 'label': 'Atualizar'},
        {'value': 'DELETE', 'label': 'Excluir'},
        {'value': 'EXPORT', 'label': 'Exportar'}
    ]
    
    # Lista de tipos de alvo disponíveis
    target_types = [
        {'value': 'User', 'label': 'Usuário'},
        {'value': 'Aluno', 'label': 'Aluno'},
        {'value': 'Caixa', 'label': 'Caixa'},
        {'value': 'ImportLog', 'label': 'Log de Importação'}
    ]
    
    return render_template('auditoria.html', 
                         pagination=pagination,
                         users=users,
                         actions=actions,
                         target_types=target_types,
                         action_translations=action_translations,
                         target_type_translations=target_type_translations,
                         user_filter=user_filter,
                         action_filter=action_filter,
                         target_type_filter=target_type_filter,
                         date_from=date_from,
                         date_to=date_to)


@app.route('/exportar-alunos', methods=['GET'])
@login_required
def exportar_alunos():
    if current_user.role != 'Administrador':
        flash('Acesso negado. Apenas administradores podem exportar dados.', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('exportar_alunos.html')

@app.route('/exportar-alunos/processar', methods=['POST'])
@login_required
def processar_exportacao():
    if current_user.role != 'Administrador':
        return jsonify({'error': 'Acesso negado.'}), 403

    import pandas as pd
    import io
    import json
    import os
    from flask import stream_with_context

    def generate():
        try:
            timestamp = get_local_time().strftime("%Y%m%d_%H%M%S")
            file_name = f"exportacao_alunos_{timestamp}.xlsx"
            upload_folder = os.path.join(app.root_path, 'static', 'downloads')
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
            file_path = os.path.join(upload_folder, file_name)

            yield json.dumps({"status": "info", "message": "Iniciando exportação...", "percent": 5}) + '\n'

            with app.app_context():
                total_alunos = Aluno.query.count()
                
                if total_alunos == 0:
                    yield json.dumps({"status": "error", "message": "Nenhum aluno encontrado para exportar."}) + '\n'
                    return
                
                yield json.dumps({"status": "start", "message": f"Preparando {total_alunos} alunos...", "percent": 10, "total": total_alunos}) + '\n'

                data = []
                BATCH_SIZE = 500
                processed = 0

                # Processar alunos em lotes para manter a conexão aberta e atualizar o progresso
                for offset in range(0, total_alunos, BATCH_SIZE):
                    batch = Aluno.query.outerjoin(Caixa).order_by(Caixa.letra, Caixa.numero, Aluno.nome).offset(offset).limit(BATCH_SIZE).all()
                    
                    for aluno in batch:
                        data.append({
                            'Nome': aluno.nome,
                            'Data de Nascimento': aluno.data_nascimento.strftime('%d/%m/%Y') if aluno.data_nascimento else '',
                            'Nome da mãe': aluno.nome_mae or '',
                            'Nome do pai': aluno.nome_pai or '',
                            'Caixa': aluno.caixa.nome_formatado if aluno.caixa else '',
                            'Status': 'Ativo' if aluno.ativo else 'Inativo'
                        })
                        processed += 1
                        
                    percent = 10 + int((processed / total_alunos) * 70) # Takes 70% of progress
                    yield json.dumps({"status": "progress", "percent": percent, "processed": processed, "total": total_alunos, "message": f"Processando dados ({processed}/{total_alunos})"}) + '\n'

                yield json.dumps({"status": "info", "message": "Gerando arquivo Excel (processo final)...", "percent": 85}) + '\n'

                df = pd.DataFrame(data)
                
                with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='Alunos', index=False)
                    
                yield json.dumps({"status": "info", "message": "Finalizando e gravando LOG...", "percent": 95}) + '\n'
                
                log_audit('EXPORT', 'Aluno', details=f"Exportados {len(data)} alunos via Excel")
                db.session.commit()
                
                download_url = url_for('static', filename=f'downloads/{file_name}')
                
                yield json.dumps({"status": "complete", "message": "Exportação concluída com sucesso!", "percent": 100, "download_url": download_url}) + '\n'

        except Exception as e:
            yield json.dumps({"status": "error", "message": str(e)}) + '\n'

    return app.response_class(stream_with_context(generate()), mimetype='application/json')

if __name__ == '__main__':
    app.run(debug=True)

