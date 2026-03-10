# Publicando o SISCAP no Render.com (Custo Zero)

Este guia apresenta todas as etapas necessárias para realizar o deploy do **SISCAP** de forma eficiente, persistente e com **custo zero**, utilizando o **Render.com** para hospedar o aplicativo Flask e uma provedor externo (como **Supabase** ou **Neon.tech**) para fornecer um banco de dados PostgreSQL gratuito.

Esta arquitetura garante que:
1. As imagens persistam em um disco vinculado à aplicação no Render.
2. O banco de dados não consuma recursos tarifados por estar hospedado de maneira otimizada (serverless).

---

## 🛠️ Passo 1: Configurar um Banco de Dados PostgreSQL Gratuito

Você pode escolher entre duas excelentes opções gratuitas para hospedar seu banco de dados PostgreSQL: **Supabase** ou **Neon.tech**. Siga as instruções de apenas uma delas.

### Opção A: Usando o Supabase (Recomendado)
1. Crie uma conta no [Supabase](https://supabase.com/).
2. Clique em **"New Project"**.
3. Escolha um nome para o projeto (ex: `siscap-db`) e defina uma senha forte para o banco de dados. Guarde esta senha.
4. Escolha a região mais próxima (ex: "South America (São Paulo)").
5. Após o projeto ser provisionado, vá em **Project Settings** (ícone de engrenagem) > **Database**.
6. Role a página até encontrar a seção **Connection string** e selecione a aba **URI**.
7. Copie a connection string, que será parecida com:
   `postgresql://postgres.[referencia]:[sua-senha]@aws-0-[regiao].pooler.supabase.com:6543/postgres`
8. Lembre-se de substituir `[sua-senha]` na URL copiada pela senha que você criou no passo 3. Essa URL final será a sua `DATABASE_URL`.

### Opção B: Usando o Neon.tech
1. Crie uma conta no [Neon.tech](https://neon.tech/).
2. Após o login, crie um novo projeto (ex: `siscap-db`).
3. O Neon irá fornecer uma **Connection String** logo na tela inicial, no formato:
   `postgresql://[user]:[password]@[host]/[dbname]?sslmode=require`
4. Copie essa URL completa (ela já conterá a senha oculta ou pedirá para revelá-la). Ela será a sua `DATABASE_URL`.

---

## 🚀 Passo 2: Publicar o App no Render.com (via Blueprint)

O repositório do projeto possui um arquivo `render.yaml` pronto para configurar toda a infraestrutura da máquina do Render (Web Service e Disco persistente para os uploads de imagens).

1. Faça **commit e push** de todas as mudanças recentes (incluindo o arquivo `render.yaml`) para o seu repositório no GitHub.
2. Acesse o [Render Dashboard](https://dashboard.render.com).
3. No menu superior da plataforma, clique em **New** > **Blueprint**.
4. Conecte sua conta do GitHub e selecione o repositório do `SISCAP`.
5. O Render lerá o arquivo `render.yaml` e montará a seguinte estrutura:
   - **Web Service:** Seu aplicativo Python será criado.
   - **Variáveis de Ambiente:** Uma chave segura (`SECRET_KEY`) para o Flask será gerada aleatoriamente.
   - **Disco Persistente:** O Render ativará um disco de 1GB na rota `/opt/render/project/src/static/uploads` garantindo que as **imagens (fundos de login, favicons, etc) não sejam apagadas** a cada reinicialização da máquina gratuita.
6. Aprove a criação e aguarde o provisionamento inicial.

---

## 🔗 Passo 3: Conectar o Banco de Dados ao Render

Para que o Sistema funcione, ele precisa saber onde está o banco de dados (Supabase ou Neon):

1. No dashboard do [Render](https://dashboard.render.com), vá até o **Dashboard** e clique no seu Web Service (ex: `siscap-web`).
2. No menu lateral esquerdo, clique em **Environment**.
3. Role até a seção **Environment Variables** e clique em **Add Environment Variable**.
4. Crie a variável responsável pela conexão com o banco de dados:
   - **Key:** `DATABASE_URL`
   - **Value:** Cole aqui aquela _Connection String_ (`postgresql://...`) que você preparou no Passo 1 (lembrando de colocar a senha caso tenha usado o Supabase).
5. Clique em **Save Changes**. O Render começará um novo deploy (build) automaticamente aplicando essa variável.

---

## 🔒 Considerações Finais

Após o site estar no ar e o domínio ser liberado (ex: `https://siscap-web.onrender.com`):

1. **Acesso e Criação Automática:** Assim que você abrir o link do sistema pela primeira vez, o código da aplicação detectará a presença da `DATABASE_URL` e criará todas as tabelas e configurações do banco de dados automaticamente. Não é necessário rodar scripts SQL manuais.
2. **Imagens Persistentes:** Graças ao disco configurado via Blueprint, sempre que você usar o menu de "Configurações" interno da plataforma para alterar a imagem de fundo ou favicon, essa imagem permanecerá salva imune aos reboots do plano Free.
3. Se a string do Supabase ou Neon fornecida vier com o formato `postgres://`, o arquivo `config.py` interno do SISCAP já tratará essa alteração automaticamente para `postgresql://` adequando o aplicativo para o driver `psycopg2-binary` usado debaixo dos panos pelo SQLAlchemy.
