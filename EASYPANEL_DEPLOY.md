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
   - **Version**: 16 (ou latest)
   - **Database Name**: `cntecidos`
   - **Username**: `cntecidos`
   - **Password**: (gerar senha forte)
4. Clique em **Deploy**
5. **Anote o hostname interno**: `db` (usado no DATABASE_URL)

### 3. Adicionar App Service

1. Clique em **Add Service**
2. Selecione **App**
3. Configure:
   - **Name**: `app`
   - **Type**: Custom Dockerfile
4. Na seção **Dockerfile**:
   - **Dockerfile Path**: `backend/Dockerfile`
   - **Build Context**: `/` (raiz do repositório)

### 4. Configurar Variáveis de Ambiente

Na aba **Env** do serviço `app`, adicione:

```
PORT=3000
DATABASE_URL=postgresql://cntecidos:<senha>@db:5432/cntecidos
EVOLUTION_API_URL=https://evolution-api.seu-dominio.com
EVOLUTION_INSTANCE=cn_tecidos
EVOLUTION_API_KEY=<sua_chave>
AUTHENTICATION_API_KEY=<sua_chave_api>
GEMINI_API_KEY=<sua_chave_gemini>
HANDOFF_LINK=https://wa.me/5511999999999
```

**Importante**: Substitua `<senha>` pela senha do PostgreSQL definida no passo 2.

### 5. Configurar Domínio (opcional)

1. Na aba **Domain** do serviço `app`:
2. Clique em **Add Domain**
3. Adicione subdomain (ex: `api.seudominio.com`)
4. Configure SSL se necessário

### 6. Health Check

O Dockerfile já inclui health check configurado:

```
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:${PORT:-3000}/health', timeout=5)" || exit 1
```

Easypanel usará automaticamente `/health` para verificar o status.

### 7. Deploy

1. Clique em **Deploy** no serviço `app`
2. Aguarde o build finalizar (pode levar alguns minutos)
3. Verifique os logs em **Logs** para confirmar inicialização

### 8. Verificar

Acesse:

- `https://api.seudominio.com/health` → `{"status": "ok", "service": "cn_tecidos_ai", "version": "1.0.0"}`
- `https://api.seudominio.com/` → `{"status": "ok", ...}`

## Troubleshooting

### Build falha

Verifique os logs de build:
```
docker logs cn-tecidos-app
```

### App não inicia

1. Verifique se o banco está acessível
2. Confirme DATABASE_URL está correto
3. Cheque os logs: `docker logs cn-tecidos-app`

### Health check falha

O health check requer httpx. Se falhar, verifique se o app iniciou corretamente nos logs.
