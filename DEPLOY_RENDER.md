# Publicando o SISCAP no Render.com (Custo Zero Real)

Este guia apresenta o caminho para realizar o deploy do **SISCAP** com **custo zero**, utilizando o plano **Free** do Render. 

> [!IMPORTANT]
> No Render, o uso de "Discos Persistentes" (via Blueprints) **possui custo mensal**. Para manter o custo em zero, utilizaremos apenas o serviço de Web Service gratuito e um banco de dados externo.

---

## 🛠️ Passo 1: Configurar um Banco de Dados PostgreSQL Gratuito

O plano gratuito do Render para bancos de dados expira em 90 dias. Para uma solução permanente e gratuita, utilize o **Supabase** ou **Neon.tech**.

### Opção A: Usando o Supabase (Recomendado)
1. Crie uma conta no [Supabase](https://supabase.com/).
2. Crie um novo projeto (ex: `siscap-db`) e defina uma senha forte.
3. Vá em **Settings** > **Database** > **Connection string** > **URI**.
4. Copie a URL. Ela será sua `DATABASE_URL`. Substitua `[YOUR-PASSWORD]` pela senha que você criou.

---

## 🚀 Passo 2: Criar o Web Service no Render (Manual - Custo Zero)

Para evitar cobranças, **NÃO** utilize a opção "Blueprints". Siga estes passos:

1. Acesse o [Render Dashboard](https://dashboard.render.com).
2. Clique em **New +** > **Web Service**.
3. Conecte seu repositório do GitHub.
4. Preencha as configurações básicas:
   - **Name:** `siscap-web`
   - **Environment:** `Python 3`
   - **Region:** Escolha uma próxima de você.
   - **Branch:** `main` (ou a sua branch principal).
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
5. **Instância:** Certifique-se de selecionar o plano **Free** ($0/month).

---

## 🔗 Passo 3: Configurar Variáveis de Ambiente

Ainda na tela de criação (ou na aba **Environment** do serviço já criado):

1. Clique em **Add Environment Variable** e adicione:
   - **Key:** `DATABASE_URL` | **Value:** (Sua URL do Supabase ou Neon)
   - **Key:** `FLASK_ENV` | **Value:** `production`
   - **Key:** `PYTHON_VERSION` | **Value:** `3.11.0`
   - **Key:** `SECRET_KEY` | **Value:** (Uma sequência longa de letras e números aleatórios)

---

## ⚠️ Limitação do Plano Gratuito (Custo Zero)

No plano gratuito do Render, o sistema de arquivos é **efêmero**. Isso significa que:
1. Fotos de perfil, Favicons ou Imagens de Fundo enviadas pelo usuário **serão apagadas** sempre que o servidor reiniciar (o que ocorre pelo menos uma vez por dia).
2. **Solução Recomendada:** Para manter as imagens permanentes sem custo, você deve inserir os links diretos de imagens hospedadas na internet (ex: Imgur, PostImages) nos campos de configuração do sistema, em vez de fazer o upload do arquivo.

> [!TIP]
> O banco de dados (alunos, usuários e logs) permanecerá **100% seguro e salvo** no Supabase/Neon, pois ele não depende do disco do Render.
