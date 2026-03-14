# Publicando o SISCAP no Render.com (Custo Zero Real)

Este guia apresenta o caminho para realizar o deploy do **SISCAP** com **custo zero**, utilizando o plano **Free** do Render e o banco de dados **Supabase**.

> [!IMPORTANT]
> No Render, o uso de "Discos Persistentes" (via Blueprints) **possui custo mensal**. Para manter o custo em zero, utilizaremos apenas o serviço de Web Service gratuito e um banco de dados externo.

---

## 🛠️ Passo 1: Configurar o Banco de Dados no Supabase

O banco de dados é onde ficarão salvos os alunos, usuários e logs. Ele é independente do Render e persistente.

1.  Crie uma conta no [Supabase](https://supabase.com/).
2.  Crie um novo projeto (ex: `siscap-prod`).
3.  Defina uma senha forte. **Anote esta senha**, ela será usada na URL de conexão.
4.  Aguarde a finalização do provisionamento do banco.
5.  No menu lateral, vá em **Project Settings** (ícone de engrenagem) > **Database**.
6.  Role até a seção **Connection string**, selecione a aba **URI**.
7.  Copie a URL. Ela terá este formato:
    `postgresql://postgres.[referencia]:[SUA-SENHA]@aws-0-[regiao].pooler.supabase.com:6543/postgres`
    *(Substitua `[SUA-SENHA]` pela senha que você definiu no passo 3).*

---

## 🚀 Passo 2: Criar o Web Service no Render

1.  Acesse o [Render Dashboard](https://dashboard.render.com).
2.  Clique em **New +** > **Web Service**.
3.  Conecte seu repositório do GitHub (onde está o código do SISCAP).
4.  Configure os detalhes do serviço:
    *   **Name:** `siscap-web`
    *   **Environment:** `Python 3`
    *   **Build Command:** `pip install -r requirements.txt`
    *   **Start Command:** `gunicorn app:app`
5.  **Plano de Instância:** Selecione obrigatoriamente o plano **Free** ($0/month).

---

## 🔗 Passo 3: Configurar Variáveis de Ambiente

No painel do seu serviço no Render, vá na aba **Environment** e adicione as seguintes chaves. O sistema usará estas informações para criar as tabelas e o administrador inicial automaticamente.

### Variáveis Obrigatórias
*   **`DATABASE_URL`**: Cole a URL que você preparou no Passo 1 (com a senha correta).
*   **`FLASK_ENV`**: `production`
*   **`PYTHON_VERSION`**: `3.14.3`
*   **`SECRET_KEY`**: (Uma sequência longa de letras e números aleatórios).

### Variáveis do Administrador Inicial (Opcional)
Se estas chaves não forem preenchidas, o sistema usará os valores padrão entre parênteses:
*   **`ADMIN_USERNAME`**: Nome de usuário (padrão: `admin`)
*   **`ADMIN_PASSWORD`**: Senha de acesso (padrão: `admin123`)
*   **`ADMIN_EMAIL`**: E-mail do administrador (padrão: `admin@example.com`)
*   **`ADMIN_CPF`**: CPF do administrador (padrão: `000.000.000-00`)

---

## 🏗️ Passo 4: Primeiro Acesso e Ativação

O SISCAP detecta automaticamente se o banco de dados está vazio e realiza o "Seed" (semeadura) inicial.

1.  Assim que o Deploy terminar no Render ("Deploy Live"), acesse a URL do seu sistema.
2.  **Tudo Automático:** O sistema criará as tabelas e o primeiro usuário administrador (usando os dados das variáveis de ambiente que você configurou no Passo 3).
3.  Faça o login com o usuário e senha definidos.

---

## ⚠️ Observações sobre Custo Zero

*   **Imagens Efêmeras:** No plano gratuito, se você fizer upload de um Favicon ou Fundo de Login, ele sumirá se o servidor reiniciar. Para imagens permanentes, use links da internet (Imgur, etc.) nas configurações.
*   **Banco de Dados Seguro:** Seus dados de alunos e usuários estão **seguros no Supabase** e não serão apagados.
*   **Modo de Espera:** Se o sistema ficar sem acessos por algum tempo, o Render coloca a aplicação para "dormir". O primeiro acesso pode demorar cerca de 1 minuto para carregar.
