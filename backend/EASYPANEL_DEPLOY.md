# Deploy C&N Tecidos AI Agent — Guia Completo Passo-a-Passo

## Visão Geral da Arquitetura

```
┌─────────────────────────────────────────────────────────────────────┐
│                         WhatsApp User                               │
│                    (cliente enviando mensagem)                       │
└─────────────────────────────────────┬───────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Evolution API (VPS)                             │
│              URL: https://aidos-evolution-api...easypanel.host      │
│                   • QR Code já escaneado ✅                         │
│                   • Instância: cn_tecidos                           │
└─────────────────────────────────────┬───────────────────────────────┘
                                      │ Webhook POST
                                      │ /api/v1/evolution/webhook
                                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   C&N Tecidos AI Agent                             │
│                  (Easypanel App Service)                            │
│                                                                     │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────────┐ │
│  │  FastAPI     │   │  LangGraph   │   │   PostgreSQL             │ │
│  │  /health    │   │  (fashion_   │   │   (cntecidos)           │ │
│  │  /api/v1/   │──▶│   graph)     │──▶│                          │ │
│  │  evolution  │   │              │   │                          │ │
│  │  /webhook   │   │  Gemini LLM  │   │                          │ │
│  └──────────────┘   └──────────────┘   └──────────────────────────┘ │
│         │                 │                      ▲                 │
│         │                 │                      │                 │
│         ▼                 ▼                      │                 │
│  ┌──────────────────────────────────────────────┐ │                 │
│  │              Resposta WhatsApp                 │ │                 │
│  └──────────────────────────────────────────────┘ │                 │
└────────────────────────────────────────────────────┼─────────────────┘
                                                      │
                                                      ▼
                                            ┌─────────────────┐
                                            │  Return to      │
                                            │  Evolution API  │
                                            └─────────────────┘
```

---

## Pré-requisitos

- [ ] Conta no Easypanel com VPS configurada
- [ ] Evolution API já instalada e rodando na VPS (QR Code escaneado ✅)
- [ ] Repositório GitHub: https://github.com/VMarques-io/cn-tecidos-mvp
- [ ] Chaves de API necessárias:
  - Google Gemini API Key (obtenha em https://aistudio.google.com)
  - Evolution API Key (da sua instância na VPS)

---

## Passo 1: Criar Projeto no Easypanel

1. Acesse o painel do Easypanel
2. Clique em **New Project**
3. Selecione **Blank Project**
4. Nome do projeto: `cn-tecidos-ai`
5. Clique em **Create**

---

## Passo 2: Adicionar PostgreSQL

1. Dentro do projeto `cn-tecidos-ai`, clique em **Add Service**
2. Selecione **Database** → **PostgreSQL**
3. Configure:
   | Campo | Valor |
   |-------|-------|
   | Name | `db` |
   | Database | `cntecidos` |
   | User | `cntecidos` |
   | Password | `(gere uma senha forte e salve!)` |
4. Clique em **Deploy**

**⚠️ SALVE ESSA SENHA!** Ela será usada na variável `DATABASE_URL`.

---

## Passo 3: Adicionar App Service (Build from GitHub)

1. Clique em **Add Service**
2. Selecione **App**
3. Configure o deployment:

### Configuração do App

| Campo | Valor |
|-------|-------|
| Name | `cn-tecidos-app` |
| Type | `Custom Dockerfile` |
| Repository | `https://github.com/VMarques-io/cn-tecidos-mvp` |
| Branch | `main` |
| Dockerfile Path | `backend/Dockerfile` |
| Build Context | `/` |

4. Clique em **Configure**

### Variáveis de Ambiente

Adicione as seguintes variáveis de ambiente (Environment Variables):

```env
# ============================================
# CONFIGURAÇÃO OBRIGATÓRIA
# ============================================

# Porta do servidor (NÃO MUDAR)
PORT=3000

# ============================================
# BANCO DE DADOS (PostgreSQL)
# ============================================
# Substitua <SUA_SENHA> pela senha que você definiu no Passo 2
DATABASE_URL=postgresql://cntecidos:<SUA_SENHA>@db:5432/cntecidos

# ============================================
# EVOLUTION API (WhatsApp)
# ============================================
# URL da sua Evolution API (NÃO inclua trailing slash)
EVOLUTION_API_URL=https://aidos-evolution-api.1q56uy.easypanel.host

# Nome da instância configurada na Evolution API
EVOLUTION_INSTANCE=cn_tecidos

# Chave de API da Evolution API (encontre nas settings da instância)
EVOLUTION_API_KEY=<SUA_EVOLUTION_API_KEY>

# ============================================
# AUTENTICAÇÃO INTERNA
# ============================================
# Chave para proteger as rotas internas (gere uma string aleatória forte)
AUTHENTICATION_API_KEY=<SUA_AUTH_KEY>

# ============================================
# GOOGLE GEMINI (LLM)
# ============================================
# Chave da API do Google Gemini (obtenha em aistudio.google.com)
GEMINI_API_KEY=<SUA_GEMINI_API_KEY>

# ============================================
# HANDOFF (Encaminhamento Humano)
# ============================================
# Link do WhatsApp para encaminhamento humano
HANDOFF_LINK=https://wa.me/558335073620
```

### Slots (Recursos)

Configure os recursos do container:

| Recurso | Valor Mínimo | Recomendado |
|---------|--------------|-------------|
| CPU | 0.5 | 1.0 |
| Memory | 512MB | 1GB |

5. Clique em **Deploy**

---

## Passo 4: Aguardar Deploy

O primeiro deploy pode levar **3-5 minutos** enquanto:
- Baixa a imagem base Python 3.12
- Instala dependências (uv, requirements)
- Compila o grafo LangGraph
- Inicializa o banco de dados

### Verificar Status

1. Acesse **Logs** do serviço para acompanhar
2. Aguarde a mensagem: `🚀 C&N Tecidos AI Agent iniciando...`

### Testar Health Check

Após o deploy, teste o endpoint de saúde:

```bash
curl https://seu-dominio-easypanel/health
```

Resposta esperada:
```json
{"status":"ok","service":"cn_tecidos_ai","version":"1.0.0"}
```

---

## Passo 5: Configurar Webhook na Evolution API

Agora você precisa configurar a Evolution API para enviar mensagens ao seu agente.

### 5.1: Obtenha a URL do seu App

A URL será algo como:
```
https://cn-tecidos-ai.seu-dominio-easypanel.host
```

### 5.2: Configure o Webhook

1. Acesse a interface da Evolution API (geralmente na porta 8080 ou através do Easypanel)
2. Vá em **Settings** → **Webhooks**
3. Configure:

| Campo | Valor |
|-------|-------|
| URL | `https://cn-tecidos-ai.seu-dominio-easypanel.host/api/v1/evolution/webhook` |
| Events | `MESSAGES.UPSERT` |
| Webhook ByEvents | ✅ Ativado |
| Webhook Base64 | ❌ Desativado |

### 5.3: Defina a Instância como Primária

Se você tiver múltiplas instâncias, defina `cn_tecidos` como primária para receber webhooks.

---

## Passo 6: Testar o Agente

### Teste 1: Health Check
```bash
curl https://cn-tecidos-ai.seu-dominio/health
```

### Teste 2: Envie uma mensagem no WhatsApp

1. Escaneie o QR Code da instância `cn_tecidos` na Evolution API
2. Envie uma mensagem de teste: **"Olá"**
3. O agente deve responder com o triage inicial

### Respostas Esperadas

| Mensagem | Resposta do Agente |
|----------|-------------------|
| "Olá" | Saudação inicial + menu de opções |
| "Qual o preço do tecido X?" | FAQ sobre tecidos |
| "Quero falar com atendente" | Encaminhamento para humano |

---

## Troubleshooting

### Problema: "Connection refused" no health check

1. Verifique se o container está rodando: `docker ps`
2. Check os logs: `docker logs cn-tecidos-app`
3. Verifique se a porta 3000 está exposta corretamente

### Problema: "Database unavailable"

1. Verifique se o PostgreSQL está rodando
2. Confirme a `DATABASE_URL` com a senha correta
3. Aguarde 30 segundos após iniciar o banco

### Problema: Agent não responde no WhatsApp

1. Verifique se o webhook está configurado corretamente
2. Check os logs da Evolution API
3. Confirme que a instância está conectada (QR Code escaneado)
4. Teste o webhook manualmente:
```bash
curl -X POST https://cn-tecidos-ai.seu-dominio/api/v1/evolution/webhook \
  -H "Content-Type: application/json" \
  -d '{"event":"MESSAGES.UPSERT","instance":"cn_tecidos","data":{}}'
```

### Problema: Erro 500 Internal Server Error

1. Check os logs do agente
2. Verifique se a `GEMINI_API_KEY` está correta
3. O agente tem **graceful degradation** - se o Gemini falhar, ainda deve responder com erro amigável

---

## Limpeza: Deletar Branch `master`

O repositório tem um branch `master` (typo do `main`). Para deletar:

1. Vá para https://github.com/VMarques-io/cn-tecidos-mvp
2. Clique em **Settings** → **Branches**
3. Em "Default branch", clique no ✏️ e mude para `main` se necessário
4. Em "Protected branches", delete o branch `master`

Ou via GitHub CLI:
```bash
gh api repos/VMarques-io/cn-tecidos-mvp/branches/master -X DELETE
```

---

## Estrutura do Projeto

```
cn-tecidos-mvp/
├── backend/
│   ├── main.py                  # Entry point FastAPI
│   ├── requirements.txt         # Dependências Python
│   ├── Dockerfile               # Multi-stage build
│   ├── docker-compose.yml       # Desenvolvimento local
│   ├── .env.example            # Template de variáveis
│   ├── alembic.ini             # Migrações BD
│   ├── alembic/
│   │   └── versions/           # Histórico de migrações
│   ├── db/
│   │   └── database.py         # Conexão PostgreSQL
│   ├── models/
│   │   ├── user.py
│   │   ├── conversation.py
│   │   └── flow_state.py
│   ├── agents/
│   │   ├── state.py            # Estado do agente
│   │   ├── nodes.py            # Nós LangGraph
│   │   └── fashion_graph.py    # Grafo principal
│   ├── routes/
│   │   └── webhook.py          # Endpoint Evolution API
│   ├── services/
│   │   ├── whatsapp.py         # Integração Evolution
│   │   ├── knowledge.py        # Base de conhecimento
│   │   └── memory.py           # Memória de conversa
│   └── tests/                  # 45 testes automatizados
├── .gitignore
├── README.md
└── EASYPANEL_DEPLOY.md
```

---

## Comandos Úteis

### Ver logs do container
```bash
docker logs -f cn-tecidos-app
```

### Rebuild após mudanças
```bash
docker compose -f backend/docker-compose.yml build
docker compose -f backend/docker-compose.yml up -d
```

### Testar localmente
```bash
cd backend
cp .env.example .env
# Preencha as variáveis
docker compose up --build
curl localhost:3000/health
```

### Resetar banco de dados
```bash
docker exec -it cn-tecidos-db psql -U cntecidos -d cntecidos -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
```

---

## Variáveis de Ambiente — Resumo

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `PORT` | Porta do servidor | `3000` |
| `DATABASE_URL` | String conexão PostgreSQL | `postgresql://cntecidos:senha@db:5432/cntecidos` |
| `EVOLUTION_API_URL` | URL da Evolution API | `https://evolution-api...easypanel.host` |
| `EVOLUTION_INSTANCE` | Nome da instância WhatsApp | `cn_tecidos` |
| `EVOLUTION_API_KEY` | Chave da Evolution API | `UUID da instância` |
| `AUTHENTICATION_API_KEY` | Chave auth rotas internas | `string aleatória` |
| `GEMINI_API_KEY` | Chave Google Gemini | `AIza...` |
| `HANDOFF_LINK` | Link WhatsApp humano | `https://wa.me/558335073620` |

---

## Próximos Passos (Fora do Escopo MVP)

- [ ] Adicionar Redis para cache de sessões
- [ ] Implementar dashboard admin
- [ ] Suporte a mensagens de mídia (imagens, áudio)
- [ ] Filtros avançados por grupo
- [ ] Anamnese em 5 steps
- [ ] Consulta de estoque integrada
- [ ] LGPD/criptografia de dados

---

*Documento criado em: 2026-04-17*
*Versão do agente: 1.0.0*
*Repositório: https://github.com/VMarques-io/cn-tecidos-mvp