# Deploy do SISCAP em Produção

Este guia descreve como configurar o ambiente de produção para o sistema SISCAP.

## 1. Pré-requisitos
- Servidor Linux (Ubuntu 20.04/22.04 recomendado)
- Python 3.8+
- Nginx
- Acesso root ou sudo

## 2. Configuração do Servidor

### Atualizar pacotes
```bash
sudo apt update && sudo apt upgrade
sudo apt install python3-pip python3-venv nginx
```

### Clonar o projeto
```bash
cd /var/www
sudo git clone <repositorio_git> siscap
cd siscap
```

### Configurar Ambiente Virtual
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Configurar Variáveis de Ambiente
Crie um arquivo `.env` na raiz do projeto:
`nano .env`

Conteúdo:
```
DATABASE_URL=sqlite:////var/www/siscap/instance/siscap.db
SECRET_KEY=sua_chave_secreta_aqui
```

### Inicializar o Banco de Dados
```bash
flask db init
flask db migrate
flask db upgrade
# Ou se for a primeira vez e não usar migrations:
python3 -c "from app import db; db.create_all()"
# Criar admin inicial
flask create-admin
```

## 3. Configurar Gunicorn (Systemd)

Edite o arquivo `siscap.service` incluído no projeto se necessário, e copie para o systemd:
```bash
sudo cp siscap.service /etc/systemd/system/
sudo systemctl start siscap
sudo systemctl enable siscap
```

## 4. Configurar Nginx

Copie a configuração do nginx:
```bash
sudo cp nginx_siscap.conf /etc/nginx/sites-available/siscap
sudo ln -s /etc/nginx/sites-available/siscap /etc/nginx/sites-enabled
sudo rm /etc/nginx/sites-enabled/default  # Se necessário
sudo nginx -t
sudo systemctl restart nginx
```

## 5. Firewall (UFW)
```bash
sudo ufw allow 'Nginx Full'
```

Agora o sistema deve estar acessível pelo IP do servidor.
