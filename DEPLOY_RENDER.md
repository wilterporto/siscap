# Publicando o SISCAP no Render.com com Neon.tech (Custo Zero)

Este guia apresenta todas as etapas necessárias para realizar o deploy do **SISCAP** de forma eficiente, persistente e com **custo zero**, utilizando a plataforma **Render.com** para hospedar o app Flask e a plataforma **Neon.tech** como banco de dados PostgreSQL serverless.

Esta solução garante que as imagens fiquem a salvo no disco que vincularemos à aplicação, e que o banco de dados não consuma recursos tarifados por rodar fora do Render.

---

## 🛠️ Passo 1: Configurar Banco de Dados no Neon.tech

1. Crie uma conta no [Neon.tech](https://neon.tech/) (você pode usar sua conta do GitHub ou Google).
2. Após o login, crie um novo projeto (ex: `siscap-db`).
3. O Neon irá fornecer uma **Connection String** no formato:
   `postgresql://[user]:[password]@[host]/[dbname]?sslmode=require`
4. Copie essa URL. Você irá utilizá-la em breve.

---

## 🚀 Passo 2: Publicar o App no Render.com (via Blueprint)

O repositório possui um arquivo `render.yaml` pronto para configurar toda a infraestrutura da máquina do Render (Web Service e Disco persistente para os uploads de imagens).

1. Faça **commit e push** de todas as mudanças recentes (incluindo o `requirements.txt`, `config.py` e `render.yaml`) para o seu repositório no GitHub.
2. Acesse o [Render Dashboard](https://dashboard.render.com).
3. No menu superior da plataforma, clique em **New** > **Blueprint**.
4. Conecte sua conta do GitHub e selecione o repositório do `SISCAP`.
5. O Render lerá o arquivo `render.yaml` e montará a estrutura:
   - **Web Service:** Seu aplicativo Python será criado.
   - **Variáveis (`SECRET_KEY`):** Uma chave segura para o Flask será gerada aleatoriamente.
   - **Disco Persistente (Uploads):** O Render ativará um disco de 1GB na rota `/opt/render/project/src/static/uploads` para que as **imagens (logomarca, favicons, etc) NÃO SEJAM APAGADAS** a cada reinicialização da máquina gratuita.
6. Aprove a criação.

---

## 🔗 Passo 3: Conectar o Neon.tech ao Render

Para que o Sistema funcione, ele precisa saber onde está o banco de dados:

1. No dashboard do [Render](https://dashboard.render.com), vá até o **Dashboard** e clique no seu Web Service (`siscap-web`).
2. No menu lateral esquerdo do Web Service, clique em **Environment**.
3. Clique em **Add Environment Variable**.
4. Crie a variável responsável pela conexão com o banco de dados:
   - **Key:** `DATABASE_URL`
   - **Value:** Cole aqui aquela _Connection String_ (`postgresql://...`) que você copiou do Neon.tech no Passo 1.
5. Clique em **Save Changes**. O Render começará um novo deploy (build) automaticamente para aplicar a variável.

---

## 🔒 Considerações Finais

Após o site estar no ar e o domínio ser liberado (ex: `https://siscap-web.onrender.com`):

1. **Acesso Automático:** Assim que você abrir o link do sistema pela primeira vez, o Flask detectará a URL do banco de dados (Neon) e **criará todas as tabelas e colunas** automaticamente.
2. **Imagens Persistentes:** Graças ao disco configurado, sempre que um usuário enviar uma imagem para o sistema (foto do login, favicon, etc.), ela persistirá, independentemente dos reboots da camada free do Render.
3. Se o banco do Neon estiver com outro formato de URL (como `postgres://`), não se preocupe: o arquivo `config.py` interno da aplicação já está programado para ajustá-la e o pacote `psycopg2-binary` já está sendo usado para permitir essa comunicação com maestria.
