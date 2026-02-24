# Implementação de Auditoria e Timeout de Sessão - SISCAP

## Resumo das Implementações

Este documento descreve as implementações realizadas para adicionar recursos de **auditoria completa** e **timeout de sessão por inatividade** ao sistema SISCAP.

---

## 1. Sistema de Auditoria

### 1.1 Funcionalidades Implementadas

✅ **Registro Automático de Ações**
- Todas as ações dos usuários são registradas automaticamente no banco de dados
- Tipos de ações registradas:
  - `LOGIN` - Login de usuário
  - `LOGOUT` - Logout de usuário
  - `CREATE` - Criação de registros (Alunos, Caixas, Usuários)
  - `UPDATE` - Atualização de registros
  - `DELETE` - Exclusão de registros

✅ **Interface de Visualização**
- Nova página de auditoria acessível em: **Administração > Auditoria**
- Tabela com todos os registros de auditoria
- Informações exibidas:
  - Data e hora da ação
  - Usuário que realizou a ação
  - Tipo de ação (com badges coloridos)
  - Tipo de alvo (User, Aluno, Caixa, etc.)
  - Detalhes adicionais da ação

✅ **Filtros Avançados**
- Filtro por usuário
- Filtro por tipo de ação (LOGIN, LOGOUT, CREATE, UPDATE, DELETE)
- Filtro por tipo de alvo (User, Aluno, Caixa, ImportLog)
- Filtro por período (data inicial e data final)
- Botão para limpar todos os filtros

✅ **Paginação**
- Listagem limitada a 30 registros por página
- Navegação completa: primeira página, anterior, próxima, última página
- Indicador de página atual e total de registros

### 1.2 Modelo de Dados

O modelo `Audit` já existia no sistema e foi expandido para registrar:
- `user_id` - ID do usuário que realizou a ação
- `action` - Tipo de ação realizada
- `target_type` - Tipo de entidade afetada
- `target_id` - ID da entidade afetada
- `details` - Detalhes adicionais em texto
- `timestamp` - Data e hora da ação

### 1.3 Pontos de Auditoria

Os seguintes pontos do sistema agora registram auditoria:

**Autenticação:**
- Login de usuário
- Logout de usuário

**Gerenciamento de Usuários:**
- Criação de usuário
- Atualização de usuário
- Exclusão de usuário
- Alteração de status (ativo/inativo)

**Gerenciamento de Alunos:**
- Criação de aluno
- Atualização de aluno
- Exclusão de aluno

**Gerenciamento de Caixas:**
- Criação de caixa
- Atualização de caixa
- Exclusão de caixa

**Importações:**
- Exclusão de logs de importação

---

## 2. Timeout de Sessão por Inatividade

### 2.1 Funcionalidades Implementadas

✅ **Timeout Automático**
- Sessão expira após **10 minutos de inatividade**
- Usuário é automaticamente deslogado
- Mensagem clara informando sobre a expiração da sessão

✅ **Rastreamento de Atividade**
- Cada requisição do usuário atualiza o timestamp de última atividade
- Sistema verifica automaticamente a inatividade antes de processar cada requisição

✅ **Sessão Permanente**
- Configuração de sessão permanente com lifetime de 10 minutos
- Sessão é renovada a cada atividade do usuário

### 2.2 Implementação Técnica

**Configuração no `create_app()`:**
```python
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=10)
```

**Middleware `@app.before_request`:**
- Verifica se o usuário está autenticado
- Compara o timestamp da última atividade com o horário atual
- Se passou mais de 10 minutos, faz logout automático
- Atualiza o timestamp a cada requisição

**Inicialização no Login:**
- Ao fazer login, a sessão é marcada como permanente
- Timestamp inicial é registrado

**Limpeza no Logout:**
- Ao fazer logout (manual ou automático), a sessão é completamente limpa

---

## 3. Alterações nos Arquivos

### 3.1 Backend (Python)

**`app.py`:**
- Adicionada importação de `session` e `timedelta`
- Configuração de `PERMANENT_SESSION_LIFETIME`
- Middleware `check_session_timeout()` para verificar inatividade
- Rota `/auditoria` com filtros e paginação
- Atualização da rota de login para inicializar sessão
- Atualização da rota de logout para registrar auditoria

### 3.2 Frontend (HTML)

**`templates/base.html`:**
- Adicionado link "Auditoria" no menu dropdown de Administração
- Ícone: `bi-clipboard-data-fill`

**`templates/auditoria.html` (NOVO):**
- Template completo para visualização de auditoria
- Formulário de filtros
- Tabela responsiva com registros
- Paginação completa
- Estilização consistente com o tema do sistema

---

## 4. Como Usar

### 4.1 Acessar a Auditoria

1. Faça login no sistema
2. Clique em **Administração** no menu superior
3. Selecione **Auditoria**
4. Visualize todos os registros de ações do sistema

### 4.2 Filtrar Registros

1. Na página de Auditoria, use os filtros disponíveis:
   - **Usuário:** Selecione um usuário específico
   - **Ação:** Filtre por tipo de ação (LOGIN, CREATE, etc.)
   - **Tipo de Alvo:** Filtre por entidade (User, Aluno, Caixa)
   - **Data Inicial/Final:** Defina um período
2. Clique no botão de busca (ícone de lupa)
3. Para limpar os filtros, clique em "Limpar Filtros"

### 4.3 Timeout de Sessão

- O sistema monitora automaticamente a atividade
- Após **10 minutos sem interação**, você será deslogado
- Uma mensagem informará sobre a expiração da sessão
- Basta fazer login novamente para continuar

---

## 5. Segurança e Boas Práticas

✅ **Rastreabilidade Completa**
- Todas as ações críticas são registradas
- Impossível realizar ações sem deixar rastro
- Histórico completo para auditoria e compliance

✅ **Proteção contra Sessões Abandonadas**
- Sessões inativas são automaticamente encerradas
- Reduz o risco de acesso não autorizado
- Conformidade com boas práticas de segurança

✅ **Informações Detalhadas**
- Cada registro de auditoria contém contexto suficiente
- Facilita investigação de incidentes
- Suporta análise de comportamento de usuários

---

## 6. Observações Técnicas

### 6.1 Banco de Dados

O modelo `Audit` já existia no banco de dados. Nenhuma migração foi necessária.

### 6.2 Performance

- A verificação de timeout é executada antes de cada requisição
- Impacto mínimo na performance (operação em memória)
- Registros de auditoria são inseridos de forma assíncrona

### 6.3 Compatibilidade

- Funciona com todas as versões do Flask utilizadas no projeto
- Compatível com SQLite (banco de dados atual)
- Pode ser facilmente adaptado para PostgreSQL ou MySQL

---

## 7. Próximos Passos (Opcional)

Melhorias futuras que podem ser implementadas:

- [ ] Exportação de relatórios de auditoria em CSV/Excel
- [ ] Gráficos de atividade por usuário
- [ ] Alertas automáticos para ações suspeitas
- [ ] Retenção de dados de auditoria (arquivamento automático)
- [ ] Dashboard de auditoria com métricas
- [ ] Configuração personalizável do timeout de sessão

---

## 8. Suporte

Para dúvidas ou problemas relacionados a estas funcionalidades, consulte:
- Logs do sistema em `static/uploads/`
- Registros de auditoria na interface web
- Documentação do Flask: https://flask.palletsprojects.com/

---

**Data de Implementação:** 17/02/2026  
**Versão do Sistema:** SISCAP v2.0  
**Desenvolvedor:** Antigravity AI
