from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=True) # "Nome"
    cpf = db.Column(db.String(14), unique=True, nullable=True) # Formatted CPF 000.000.000-00
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(200), nullable=False)
    active = db.Column(db.Boolean, default=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class SystemConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    smtp_server = db.Column(db.String(120), nullable=True)
    smtp_port = db.Column(db.Integer, default=587)
    smtp_username = db.Column(db.String(120), nullable=True)
    smtp_password = db.Column(db.String(120), nullable=True)
    smtp_use_tls = db.Column(db.Boolean, default=True)
    smtp_sender_email = db.Column(db.String(120), nullable=True)
    login_image = db.Column(db.String(200), nullable=True) # Path relative to static folder (e.g. 'img/login_bg.jpg')
    favicon_path = db.Column(db.String(200), nullable=True) # Path relative to static folder

class Audit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    action = db.Column(db.String(50), nullable=False) # CREATE, UPDATE, DELETE, LOGIN
    target_type = db.Column(db.String(50), nullable=False) # Aluno, User, Caixa
    target_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('audits', lazy=True))

class Caixa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    letra = db.Column(db.String(1), nullable=False)
    numero = db.Column(db.Integer, nullable=False)
    __table_args__ = (db.UniqueConstraint('letra', 'numero', name='_letra_numero_uc'),)

    def __repr__(self):
        return f'{self.letra}{self.numero}'

    @property
    def nome_formatado(self):
        return f"{self.letra}{self.numero}"

class Aluno(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    data_nascimento = db.Column(db.Date, nullable=True)
    nome_mae = db.Column(db.String(100), nullable=True)
    nome_pai = db.Column(db.String(100), nullable=True)
    caixa_id = db.Column(db.Integer, db.ForeignKey('caixa.id'), nullable=False)
    ativo = db.Column(db.Boolean, default=False)
    homonimo_verificado = db.Column(db.Boolean, default=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    caixa = db.relationship('Caixa', backref=db.backref('alunos', lazy=True))
    created_by = db.relationship('User', backref=db.backref('created_students', lazy=True))

    def __repr__(self):
        return f'<Aluno {self.nome}>'
