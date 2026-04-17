# Deploy C&N Tecidos AI Agent no Easypanel

## Pré-requisitos
- Easypanel instalado e configurado
- Domínio configurado (opcional)

## Passo a Passo

### 1. Criar Projeto
1. Acesse o painel do Easypanel
2. Clique em **New Project**
3. Selecione **Blank Project**
4. Nomeie como `cn-tecidos-ai`
5. Clique em **Create**

### 2. Adicionar PostgreSQL
1. No projeto `cn-tecidos-ai`, clique em **Add Service**
2. Selecione **PostgreSQL**
3. Configure:
   - **Name**: `db`
   - **Version**: 16
   - **Database Name**: `cntecidos`
   - **Username**: `cntecidos`
   - **Password**: (gerar senha forte)
4. Clique em **Deploy**

### 3. Adicionar App Service
1. Clique em **Add Service**
2. Selecione **App**
3. Configure:
   - **Name**: `app`
   - **Type**: Custom Dockerfile
4. Na seção **Dockerfile**:
   - **Dockerfile Path**: `backend/Dockerfile`
   - **Build Context**: `/`

### 4. Configurar Variáveis de Ambiente
```
PORT=3000
DATABASE_URL=postgresql://cntecidos:<senha>@db:5432/cntecidos
EVOLUTION_API_URL=https://aidos-evolution-api.1q56uy.easypanel.host
EVOLUTION_INSTANCE=cn_tecidos
EVOLUTION_API_KEY=<sua_chave>
AUTHENTICATION_API_KEY=<sua_chave>
GEMINI_API_KEY=<sua_chave_gemini>
HANDOFF_LINK=https://wa.me/558335073620
```

### 5. Deploy
1. Clique em **Deploy** no serviço `app`
2. Aguarde o build finalizar
3. Verifique os logs em **Logs**

### 6. Verificar
- `https://api.seudominio.com/health` → `{"status": "ok", "service": "cn_tecidos_ai", "version": "1.0.0"}`
