# Strategy AI Backend

**Production-ready FastAPI backend** for AI-powered strategic business analysis platform.

## Architecture Overview

```
strategy-ai-backend/
├── app/
│   ├── main.py                    # FastAPI app entry point
│   ├── core/                      # Core infrastructure
│   │   ├── database.py            # Supabase operations
│   │   ├── supabase.py            # Client initialization
│   │   ├── cache.py               # 3-tier Redis caching
│   │   └── security/              # Security utilities
│   │       ├── rate_limiter.py
│   │       ├── prompt_sanitizer.py
│   │       └── hallucination_detector.py
│   ├── routes/                    # API endpoints
│   │   └── auth.py                # Authentication
│   ├── services/                  # Business logic
│   │   ├── analysis/              # Strategic analysis
│   │   │   ├── enhanced.py        # Main analysis engine
│   │   │   ├── multistage.py     # Multi-stage pipeline
│   │   │   ├── deep_dive.py      # Industry deep dives
│   │   │   └── confidence_scorer.py
│   │   ├── ai/                    # AI services
│   │   │   ├── chat.py            # Report Q&A
│   │   │   ├── editor.py          # AI editing
│   │   │   └── routing.py         # Model selection
│   │   ├── data/                  # Data collection
│   │   │   ├── apify.py           # Web scraping
│   │   │   └── perplexity.py     # Market research
│   │   ├── intelligence/          # Advanced features
│   │   │   ├── dashboard.py       # Dashboard insights
│   │   │   └── memory.py          # Learning system
│   │   ├── pdf_generator.py       # PDF exports
│   │   └── report_adapter.py      # Legacy compatibility
│   ├── models/                    # Data models
│   │   └── schemas.py             # Pydantic schemas
│   └── utils/                     # Utilities
│       └── validation.py          # Input validation
├── tests/                         # Test suite
├── scripts/                       # Utility scripts
├── requirements.txt               # Dependencies
├── Procfile                       # Railway deployment
└── README.md                      # This file
```

## Features

### Core Analysis Pipeline
- **Multi-Stage Analysis**: Pre-research → Core Analysis → Deep Dives → Synthesis
- **12 Strategic Frameworks**: Porter's 5 Forces, SWOT, BCG Matrix, Ansoff, Blue Ocean, etc.
- **Adaptive Model Routing**: Automatic selection between GPT-4o, Gemini Flash, Claude based on task
- **Cost Optimization**: $15-20 per full analysis (90%+ cost reduction vs GPT-4o only)

### Data Collection
- **Web Scraping**: Apify integration for company website analysis
- **Market Research**: Perplexity API for industry insights
- **Multi-Source Intelligence**: Combines web scraping, AI research, and user-provided documents

### AI-Powered Features
- **Report Chat**: OpenRouter-based Q&A on analysis reports
- **AI Editing**: Natural language report modifications
- **Institutional Memory**: Learns from past analyses to improve future results
- **Dashboard Intelligence**: AI-generated insights for company dashboards

### Quality & Security
- **Language Validation**: Enforces Portuguese output (prevents English leakage)
- **Source Attribution**: Validates quantitative claims have sources
- **Hallucination Detection**: Flags unsupported data points
- **Prompt Injection Protection**: Sanitizes user inputs
- **Rate Limiting**: Upstash Redis-based request throttling

### Performance
- **3-Tier Caching**: Dashboard (5min), Reports (30min), Enrichment (24hr)
- **Confidence Scoring**: 0-100 quality scores with 5 components
- **Data Quality Assessment**: Legendary/Full/Good/Partial/Minimal tiers

## Setup

### 1. Prerequisites
- Python 3.11+
- Supabase account
- OpenRouter API key
- Upstash Redis instance
- Apify account (optional)
- Perplexity API key (optional)

### 2. Environment Variables

Create `.env` file:

```bash
# Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key
DATABASE_URL=postgresql://user:pass@host:5432/db

# AI Models
OPENROUTER_API_KEY=sk-or-v1-...
PERPLEXITY_API_KEY=pplx-...

# Caching & Rate Limiting
UPSTASH_REDIS_REST_URL=https://your-redis.upstash.io
UPSTASH_REDIS_REST_TOKEN=your-token

# Web Scraping
APIFY_API_TOKEN=apify_api_...

# Authentication
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=10080

# Environment
ENVIRONMENT=production
ALLOWED_ORIGINS=https://yourapp.com
```

### 3. Install Dependencies

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Run Locally

```bash
# Development mode with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 5. Run Tests

```bash
pytest tests/ -v
```

## API Endpoints

### Analysis
- `POST /api/analyze` - Submit new analysis request
- `GET /api/analysis/{id}` - Get analysis results
- `POST /api/analysis/{id}/regenerate` - Regenerate analysis section

### Reports
- `GET /api/reports/{id}` - Get full report
- `POST /api/reports/{id}/edit` - AI-powered editing
- `POST /api/reports/{id}/chat` - Ask questions about report
- `GET /api/reports/{id}/pdf` - Export PDF

### Intelligence
- `POST /api/dashboard/intelligence` - Generate dashboard insights
- `GET /api/reports/{id}/confidence` - Get confidence scores

### Admin
- `GET /health` - Health check
- `GET /api/admin/stats` - System statistics (requires auth)

## Development

### Import Convention
All imports use absolute paths from `app.*`:

```python
# Correct
from app.core.database import get_db
from app.models.schemas import AnalysisRequest
from app.services.analysis.enhanced import run_analysis

# Incorrect
from database import get_db
from models import AnalysisRequest
from analysis_enhanced import run_analysis
```

### Adding New Features

1. **New Service**: Add to appropriate `app/services/` subdirectory
2. **New Route**: Add to `app/routes/` and register in `app/main.py`
3. **New Model**: Add Pydantic schema to `app/models/schemas.py`
4. **New Security Feature**: Add to `app/core/security/`

### Code Quality

```bash
# Format code
black app/ tests/

# Lint
flake8 app/ tests/

# Type checking
mypy app/
```

## Deployment

### Railway (Current)

The app is configured for Railway deployment via `Procfile`:

```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**Pre-deployment checklist**:
1. Set all environment variables in Railway dashboard
2. Ensure `ALLOWED_ORIGINS` includes your frontend domain
3. Verify Supabase connection
4. Test health endpoint after deployment

### Other Platforms

**Heroku**:
```bash
heroku create your-app-name
git push heroku main
```

**Docker**:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Cost Optimization

**Smart pipeline: Premium models for client work, budget for backend**

Analysis costs **~$0.41 per full analysis** with PREMIUM quality!

| Stage | Model | Type | Cost per Analysis |
|-------|-------|------|-------------------|
| Stage 1: Extraction | Gemini 2.5 Flash | Backend | $0.002 |
| Stage 2: Gap Analysis | Gemini 2.5 Flash | Backend | $0.003 |
| Stage 3: Strategy | **GPT-4o** | **Client-Facing** ⭐ | $0.115 |
| Stage 4: Competitive | **Gemini 2.5 Pro** | **Important** ⭐ | $0.046 |
| Stage 5: Risk Scoring | **Claude 3.5 Sonnet** | **Strategic** ⭐ | $0.120 |
| Stage 6: Polish | **Claude 3.5 Sonnet** | **Client-Facing** ⭐ | $0.120 |
| **Total Analysis** | - | - | **$0.406** |
| Data Collection (Apify) | External API | Data | $0.06 (amortized) |
| **Grand Total** | - | - | **~$0.47** ✅ |

**Philosophy**:
- 🎯 **Client-facing stages**: Use BEST models (GPT-4o, Claude Sonnet, Gemini Pro)
- 💰 **Backend stages**: Use budget models (Gemini Flash)
- ✅ **Result**: Premium quality where it matters, cost-effective overall

**Cost Breakdown:**
- 1% - Backend extraction/gaps (Gemini Flash)
- 28% - Strategic analysis (GPT-4o)
- 11% - Competitive intel (Gemini Pro)
- 29% - Risk scoring (Claude Sonnet)
- 29% - Executive polish (Claude Sonnet)
- 2% - Misc/overhead

**Why This Matters:**
- Client sees GPT-4o + Claude Sonnet quality ✨
- You pay ~$0.41 (well under $1 target!)
- Competitive advantage: Others using GPT-4o everywhere pay $2-3+ per analysis

Additional features:
- Chat: $0.01-0.05 per conversation (Claude Haiku)
- Editing: $0.10-0.20 per edit (Claude Sonnet - client-facing!)
- Dashboard Intelligence: $0.01 per insight (Gemini Flash - internal)

**Quality**: 100% premium for client deliverables!
**Strategy**: Smart model selection - right model for each job!

## Troubleshooting

### PDF Generation Fails
**Error**: `FPDFUnicodeEncodingException`
**Fix**: Ensure all bullet points use ASCII characters (`-` instead of Unicode bullets)

### CORS Errors
**Error**: `Access-Control-Allow-Origin` blocked
**Fix**: Add frontend domain to `ALLOWED_ORIGINS` in `.env`

### Database Connection Issues
**Error**: `could not connect to server`
**Fix**: Verify `SUPABASE_URL` and `SUPABASE_KEY` are correct

### Rate Limiting Triggered
**Error**: `429 Too Many Requests`
**Fix**: Wait 60 seconds or increase limits in `app/core/security/rate_limiter.py`

### Import Errors After Update
**Error**: `ModuleNotFoundError: No module named 'models'`
**Fix**: Update imports to use `app.*` namespace (see Import Convention above)

## Contributing

1. Fork repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## License

Proprietary - All rights reserved

## Support

For issues or questions:
- Check troubleshooting section above
- Review error logs in Railway dashboard
- Contact development team

---

**Last Updated**: January 2025
**Version**: 2.0.0 (Post-Reorganization)
