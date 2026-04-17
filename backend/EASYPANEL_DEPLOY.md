# Deploy C&N Tecidos AI Agent no Easypanel

## Passo a Passo

### 1. Criar Projeto
New Project → Blank → `cn-tecidos-ai`

### 2. Adicionar PostgreSQL
- Name: `db`
- Database: `cntecidos`
- User: `cntecidos`
- Password: (gerar senha forte)

### 3. Adicionar App Service
- Type: Custom Dockerfile
- Dockerfile Path: `backend/Dockerfile`
- Build Context: `/`

### 4. Variáveis de Ambiente
```
PORT=3000
DATABASE_URL=postgresql://cntecidos:<SENHA>@db:5432/cntecidos
EVOLUTION_API_URL=https://aidos-evolution-api.1q56uy.easypanel.host
EVOLUTION_INSTANCE=cn_tecidos
EVOLUTION_API_KEY=<sua_chave>
AUTHENTICATION_API_KEY=<sua_chave>
GEMINI_API_KEY=<sua_chave_gemini>
HANDOFF_LINK=https://wa.me/558335073620
```

### 5. Deploy
