# Strategy AI Backend v2.0 - FastAPI + Supabase + Apify

Production-ready FastAPI backend for Strategy AI Lead Generator with Supabase PostgreSQL, JWT authentication, Apify web scraping, and Upstash Redis rate limiting.

## 🚀 Features

### Core Functionality
- **Lead Submission API**: Public endpoint for lead capture with corporate email validation
- **AI Analysis Engine**: GPT-4o-mini powered strategic analysis reports
- **Apify Integration**: Web scraping for competitor research, industry trends, and data enrichment
- **Background Processing**: Async analysis without blocking requests

### Infrastructure
- **Supabase PostgreSQL**: Scalable cloud database with Row Level Security (RLS)
- **JWT Authentication**: Secure admin access with Supabase Auth
- **Upstash Redis**: Distributed rate limiting with TTL
- **Protected Admin Endpoints**: JWT-protected submission management

### Security
- ✅ JWT token-based authentication for admin routes
- ✅ Row Level Security (RLS) policies in Supabase
- ✅ Redis-based rate limiting (3 submissions per IP per day)
- ✅ Corporate email validation (blocks personal domains)
- ✅ CORS protection

## 🏗️ Tech Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | FastAPI | 0.115.6 |
| Language | Python | 3.11+ |
| Database | Supabase (PostgreSQL) | Latest |
| Authentication | Supabase Auth + JWT | - |
| Rate Limiting | Upstash Redis | Latest |
| Web Scraping | Apify | Latest |
| AI | OpenRouter API | gpt-4o-mini |
| Async HTTP | httpx | 0.28.1 |
| Validation | Pydantic | 2.10.5 |

## 📁 Project Structure

```
strategy-ai-backend/
├── main.py                 # FastAPI app with endpoints and auth
├── models.py               # Pydantic models (requests, responses, auth)
├── database.py             # Supabase database operations
├── supabase_client.py      # Supabase client initialization
├── auth.py                 # JWT authentication middleware
├── rate_limiter.py         # Upstash Redis rate limiting
├── apify_service.py        # Apify web scraping integration
├── analysis.py             # AI analysis engine with Apify enrichment
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variables template
├── Procfile                # Railway deployment config
├── railway.json            # Railway build configuration
└── README.md               # This file
```

## 🔧 Setup Instructions

### Prerequisites

1. **Python 3.11+** installed
2. **Supabase account** (https://supabase.com)
3. **Upstash Redis account** (https://upstash.com)
4. **Apify account** (https://apify.com)
5. **OpenRouter API key** (https://openrouter.ai)

### 1. Install Dependencies

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

### 2. Setup Supabase

1. Create a new Supabase project at https://supabase.com
2. Go to **Settings > API** and copy:
   - Project URL → `SUPABASE_URL`
   - anon/public key → `SUPABASE_ANON_KEY`
   - service_role key → `SUPABASE_SERVICE_KEY`

3. Go to **SQL Editor** and run this schema:

```sql
-- Create submissions table
CREATE TABLE IF NOT EXISTS submissions (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    company TEXT NOT NULL,
    website TEXT,
    industry TEXT NOT NULL,
    challenge TEXT,
    status TEXT DEFAULT 'pending',
    report_json TEXT,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_status ON submissions(status);
CREATE INDEX IF NOT EXISTS idx_created ON submissions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_email ON submissions(email);

-- Enable Row Level Security
ALTER TABLE submissions ENABLE ROW LEVEL SECURITY;

-- Policy: Anyone can insert (public form submission)
CREATE POLICY "Anyone can insert submissions"
    ON submissions FOR INSERT
    WITH CHECK (true);

-- Policy: Only authenticated users can view
CREATE POLICY "Authenticated users can view all submissions"
    ON submissions FOR SELECT
    USING (auth.role() = 'authenticated');

-- Policy: Only authenticated users can update
CREATE POLICY "Authenticated users can update submissions"
    ON submissions FOR UPDATE
    USING (auth.role() = 'authenticated');
```

4. Go to **Authentication > Users** and create your admin user:
   - Click "Add user"
   - Enter email and password
   - Confirm email (auto-confirm in dev mode)

### 3. Setup Upstash Redis

1. Create account at https://upstash.com
2. Create new Redis database (choose region closest to your Railway deployment)
3. Copy:
   - REST URL → `UPSTASH_REDIS_URL`
   - REST Token → `UPSTASH_REDIS_TOKEN`

### 4. Setup Apify

1. Create account at https://apify.com
2. Go to **Settings > Integrations**
3. Generate API token → `APIFY_API_TOKEN`

### 5. Create Environment File

Copy `.env.example` to `.env` and fill in your credentials:

```env
# OpenRouter
OPENROUTER_API_KEY=your_openrouter_api_key

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key
SUPABASE_ANON_KEY=your_anon_key

# JWT Secret (generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")
JWT_SECRET=your-secret-jwt-key-here

# Upstash Redis
UPSTASH_REDIS_URL=https://your-redis.upstash.io
UPSTASH_REDIS_TOKEN=your_redis_token

# Apify
APIFY_API_TOKEN=your_apify_token

# CORS (add your frontend URL)
ALLOWED_ORIGINS=http://localhost:3000,https://your-frontend.vercel.app

# Rate Limiting
MAX_SUBMISSIONS_PER_IP_PER_DAY=3
```

### 6. Run Development Server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Server runs at: **http://localhost:8000**

API Docs: **http://localhost:8000/docs**

## 📡 API Endpoints

### Public Endpoints

#### `GET /`
Health check endpoint.

**Response:**
```json
{
  "service": "Strategy AI Lead Generator API",
  "status": "running",
  "version": "2.0.0",
  "features": ["Supabase", "Authentication", "Apify Integration", "Upstash Redis"]
}
```

#### `POST /api/submit`
Submit a new lead form (public, no auth required).

**Request:**
```json
{
  "name": "João Silva",
  "email": "joao@empresa.com.br",
  "company": "Tech Startup LTDA",
  "website": "https://techstartup.com.br",
  "industry": "Tecnologia",
  "challenge": "Precisamos escalar vendas B2B"
}
```

**Response:**
```json
{
  "success": true,
  "submission_id": 123
}
```

**Features:**
- Corporate email validation (blocks Gmail, Hotmail, etc.)
- Rate limiting (3 per IP per day via Redis)
- Triggers background processing with Apify enrichment

---

### Authentication Endpoints

#### `POST /api/auth/login`
Admin login endpoint.

**Request:**
```json
{
  "email": "admin@company.com",
  "password": "your-password"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "user": {
      "id": "uuid-here",
      "email": "admin@company.com"
    }
  }
}
```

---

### Protected Admin Endpoints

All admin endpoints require `Authorization: Bearer <token>` header.

#### `GET /api/admin/submissions`
Get all submissions.

**Headers:**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "João Silva",
      "email": "joao@empresa.com.br",
      "company": "Tech Startup LTDA",
      "industry": "Tecnologia",
      "status": "completed",
      "report_json": "{...}",
      "created_at": "2025-01-15T10:30:00Z"
    }
  ]
}
```

#### `POST /api/admin/reprocess/{submission_id}`
Reprocess a failed submission.

**Headers:**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response:**
```json
{
  "success": true
}
```

## 🤖 Apify Integration

The system uses Apify for comprehensive data enrichment:

1. **Website Scraping**: Extracts company info from submitted website
2. **Competitor Research**: Finds and analyzes competitors in the industry
3. **Industry Trends**: Researches current trends and market insights
4. **Company Enrichment**: Gathers additional company data from web sources

All data is aggregated and fed into the AI analysis prompt for more accurate, data-driven strategic recommendations.

## 🔒 Security Features

### Authentication Flow

1. Admin calls `POST /api/auth/login` with email/password
2. Backend validates with Supabase Auth
3. Returns JWT token (24h expiration)
4. Admin includes token in `Authorization: Bearer <token>` header
5. Middleware validates token on protected routes

### Row Level Security (RLS)

Supabase RLS policies ensure:
- Anyone can INSERT submissions (public form)
- Only authenticated users can SELECT/UPDATE submissions
- Service role key bypasses RLS for backend operations

### Rate Limiting

- Implemented with Upstash Redis
- Key: `ratelimit:{ip_address}`
- TTL: 24 hours
- Limit: 3 submissions per IP per day
- Fails open (allows requests if Redis is down)

## 🚀 Deployment

### Railway Deployment

1. Push code to GitHub
2. Create new project on Railway
3. Connect GitHub repository
4. Add environment variables from `.env.example`
5. Railway auto-deploys using `railway.json` configuration

### Environment Variables for Production

Set these in Railway dashboard:

```env
OPENROUTER_API_KEY=...
SUPABASE_URL=...
SUPABASE_SERVICE_KEY=...
SUPABASE_ANON_KEY=...
JWT_SECRET=...  # Generate strong random string
UPSTASH_REDIS_URL=...
UPSTASH_REDIS_TOKEN=...
APIFY_API_TOKEN=...
ALLOWED_ORIGINS=https://your-frontend.vercel.app
MAX_SUBMISSIONS_PER_IP_PER_DAY=3
```

## 📊 Analysis Report Structure

The AI generates a comprehensive JSON report with:

```json
{
  "diagnostico_estrategico": {
    "forças": ["força 1", "força 2", ...],
    "fraquezas": ["fraqueza 1", ...],
    "oportunidades": ["oportunidade 1", ...],
    "ameaças": ["ameaça 1", ...]
  },
  "analise_mercado": {
    "político": "análise...",
    "econômico": "análise...",
    "social": "análise...",
    "tecnológico": "análise...",
    "ambiental": "análise...",
    "legal": "análise..."
  },
  "oportunidades_identificadas": ["oportunidade 1", ...],
  "recomendacoes_prioritarias": ["recomendação 1", ...],
  "proposta_okrs": [
    {
      "objetivo": "Objetivo 1",
      "resultados_chave": ["KR1", "KR2", "KR3"]
    }
  ]
}
```

## 🔄 Migration from v1.0

If migrating from SQLite version:

1. **Data Migration**: Export SQLite data if needed (or start fresh)
2. **Environment Variables**: Update `.env` with new services
3. **Dependencies**: Run `pip install -r requirements.txt`
4. **Database**: Run Supabase SQL schema
5. **Admin User**: Create admin user in Supabase dashboard
6. **Deploy**: Redeploy with new environment variables

## 🛠️ Development

### Testing Authentication

```bash
# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@company.com","password":"yourpassword"}'

# Use token in protected endpoint
curl -X GET http://localhost:8000/api/admin/submissions \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Testing Submission

```bash
curl -X POST http://localhost:8000/api/submit \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "email": "test@company.com",
    "company": "Test Company",
    "website": "https://example.com",
    "industry": "Tecnologia",
    "challenge": "Test challenge"
  }'
```

## 📝 License

MIT License - See LICENSE file for details

## 🤝 Contributing

This is a private project for Strategy AI. For issues or feature requests, contact the development team.

---

**Version**: 2.0.0
**Last Updated**: January 2025
**Status**: Production Ready ✅
