# Strategy AI Backend - FastAPI

FastAPI backend for the Strategy AI Lead Generator MVP. Generates AI-powered strategic business analysis reports using OpenRouter API.

## Features

- **Lead Submission API**: Capture and validate lead information
- **AI Analysis Engine**: Generate comprehensive strategic reports using GPT-4o-mini
- **Background Processing**: Async analysis without blocking requests
- **SQLite Database**: Zero-config single-file database
- **Rate Limiting**: 3 submissions per IP per day (in-memory for MVP)
- **CORS Enabled**: Supports frontend on Vercel
- **Admin Endpoints**: View, manage, and reprocess submissions

## Tech Stack

- **Framework**: FastAPI 0.115
- **Python**: 3.11
- **Database**: SQLite with aiosqlite
- **AI**: OpenRouter API (gpt-4o-mini)
- **Async HTTP**: httpx
- **Validation**: Pydantic 2.10

## Project Structure

```
strategy-ai-backend/
├── main.py                 # FastAPI app with endpoints
├── models.py               # Pydantic models for validation
├── database.py             # SQLite operations
├── analysis.py             # AI analysis engine
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variables template
├── Procfile                # Railway deployment
├── railway.json            # Railway configuration
└── README.md               # This file
```

## Quick Start

### 1. Installation

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Setup

Create `.env` file:

```env
# Required: OpenRouter API Key
OPENROUTER_API_KEY=your_key_here

# Optional: CORS origins (comma-separated)
ALLOWED_ORIGINS=http://localhost:3000,https://your-frontend.vercel.app

# Optional: Rate limiting
MAX_SUBMISSIONS_PER_IP_PER_DAY=3
```

Get your OpenRouter API key at: https://openrouter.ai/keys

### 3. Initialize Database

```bash
python database.py
```

### 4. Run Development Server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Server runs at: http://localhost:8000

API Docs: http://localhost:8000/docs

## API Endpoints

### POST /api/submit

Submit a new lead form.

**Request Body:**
```json
{
  "name": "João Silva",
  "email": "joao@empresa.com.br",
  "company": "Empresa LTDA",
  "website": "https://empresa.com.br",
  "industry": "Tecnologia",
  "challenge": "Precisamos escalar vendas"
}
```

**Response:**
```json
{
  "success": true,
  "submission_id": 123
}
```

**Validation Rules:**
- Name: min 2 characters
- Email: valid format + corporate only (no Gmail, Hotmail, etc.)
- Company: min 2 characters
- Website: valid URL (optional)
- Industry: one of [Tecnologia, Saúde, Educação, Varejo, Serviços, Indústria, Outro]
- Challenge: max 200 characters (optional)

**Rate Limit:** 3 submissions per IP per day

### GET /api/admin/submissions

Get all submissions (admin endpoint).

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "João Silva",
      "email": "joao@empresa.com.br",
      "company": "Empresa LTDA",
      "website": "https://empresa.com.br",
      "industry": "Tecnologia",
      "challenge": "Precisamos escalar vendas",
      "status": "completed",
      "report_json": "{...}",
      "error_message": null,
      "created_at": "2026-01-15T10:30:00",
      "updated_at": "2026-01-15T11:00:00"
    }
  ]
}
```

### POST /api/admin/reprocess/{id}

Reprocess a failed submission.

**Response:**
```json
{
  "success": true
}
```

## AI Analysis Structure

The AI generates a structured JSON report with:

### 1. Diagnóstico Estratégico (SWOT)
```json
{
  "forças": ["força 1", "força 2", ...],
  "fraquezas": ["fraqueza 1", "fraqueza 2", ...],
  "oportunidades": ["oportunidade 1", ...],
  "ameaças": ["ameaça 1", ...]
}
```

### 2. Análise de Mercado (PESTEL)
```json
{
  "político": "análise...",
  "econômico": "análise...",
  "social": "análise...",
  "tecnológico": "análise...",
  "ambiental": "análise...",
  "legal": "análise..."
}
```

### 3. Oportunidades Identificadas
```json
["oportunidade 1", "oportunidade 2", "oportunidade 3"]
```

### 4. Recomendações Prioritárias
```json
["top 3 ações imediatas"]
```

### 5. Proposta de OKRs
```json
[
  {
    "objetivo": "Objetivo 1",
    "resultados_chave": ["KR1", "KR2", "KR3"]
  }
]
```

## Background Processing

Analysis runs asynchronously using FastAPI's `BackgroundTasks`:

1. Form submitted → Returns immediately with `submission_id`
2. Background task triggers → Calls OpenRouter API
3. Analysis completes → Updates database with report
4. If fails → Sets status to "failed" with error message

**Timeout**: 90 seconds per analysis

## Database Schema

```sql
CREATE TABLE submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    company TEXT NOT NULL,
    website TEXT,
    industry TEXT NOT NULL,
    challenge TEXT,
    status TEXT DEFAULT 'pending',
    report_json TEXT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Status Values:**
- `pending`: Analysis in progress
- `completed`: Analysis successful
- `failed`: Analysis failed (see error_message)

## Testing

### Test Database Setup
```bash
python database.py
```

### Test AI Analysis
```bash
python analysis.py
```

Requires `OPENROUTER_API_KEY` in `.env`.

### Test Full API
```bash
# Start server
uvicorn main:app --reload

# In another terminal, test submission
curl -X POST http://localhost:8000/api/submit \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "email": "test@company.com",
    "company": "Test Company",
    "industry": "Tecnologia"
  }'
```

## Deployment to Railway

### 1. Install Railway CLI
```bash
npm install -g @railway/cli
```

### 2. Login and Initialize
```bash
railway login
railway init
```

### 3. Set Environment Variables
```bash
railway variables set OPENROUTER_API_KEY=your_key_here
railway variables set ALLOWED_ORIGINS=https://your-frontend.vercel.app
```

### 4. Deploy
```bash
railway up
```

### 5. Get Public URL
```bash
railway domain
```

Use this URL in your frontend's `NEXT_PUBLIC_API_URL` environment variable.

## Cost Optimization

- **Model**: gpt-4o-mini (~$0.15 per 1M input tokens, $0.60 per 1M output tokens)
- **Estimated Cost per Analysis**: ~$0.01-0.02
- **1000 leads/month**: ~$10-20 in AI costs
- **Railway**: Free tier includes 500 hours/month (sufficient for MVP)

## Security Notes

### For MVP
- ✅ Rate limiting (in-memory)
- ✅ CORS configured
- ✅ Input validation
- ✅ Corporate email enforcement
- ❌ No authentication on admin endpoints (secret URL)

### For Production
- Add API key authentication
- Use Redis for distributed rate limiting
- Add admin user authentication
- Implement request signing
- Add monitoring and logging
- Set up error tracking (Sentry)

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENROUTER_API_KEY` | Yes | - | Your OpenRouter API key |
| `ALLOWED_ORIGINS` | No | `http://localhost:3000` | CORS origins (comma-separated) |
| `MAX_SUBMISSIONS_PER_IP_PER_DAY` | No | `3` | Rate limit per IP |
| `DATABASE_URL` | No | `sqlite:///./database.db` | Database path |

## Monitoring

### Logs
Railway automatically captures stdout/stderr. Use:
```bash
railway logs
```

### Health Check
```bash
curl https://your-api.railway.app/
```

## Troubleshooting

### "OPENROUTER_API_KEY not set"
- Create `.env` file with your API key
- Or set environment variable: `export OPENROUTER_API_KEY=your_key`

### "Analysis timed out"
- OpenRouter may be slow during high load
- Increase timeout in `analysis.py` if needed
- Check OpenRouter status: https://status.openrouter.ai

### "Rate limit exceeded"
- Each IP limited to 3 submissions/day
- Clear with server restart (in-memory store)
- For production, use Redis with TTL

### Database locked errors
- SQLite doesn't handle high concurrency well
- For production, migrate to PostgreSQL
- For MVP, single-writer pattern is sufficient

## Development Tips

### Auto-reload on Changes
```bash
uvicorn main:app --reload
```

### View API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Test with curl
```bash
# Submit lead
curl -X POST http://localhost:8000/api/submit \
  -H "Content-Type: application/json" \
  -d @test-submission.json

# Get submissions
curl http://localhost:8000/api/admin/submissions

# Reprocess
curl -X POST http://localhost:8000/api/admin/reprocess/1
```

## Support

For issues or questions:
1. Check logs: `railway logs`
2. Verify environment variables
3. Test OpenRouter API key separately
4. Check database file exists and is writable

## License

Private - All rights reserved

---

**Built with**: FastAPI, Python 3.11, OpenRouter API, SQLite
**AI Model**: gpt-4o-mini
**Deployment**: Railway
**Status**: Phase 2 Complete ✅
