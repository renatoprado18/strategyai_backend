# Architecture Improvement Plan

## Current Issues & Future Risks

### 🔴 CRITICAL ISSUES

#### 1. **Monolithic main.py (1,834 lines, 21 routes)**
**Problem**: All API routes embedded in `main.py` instead of separated by domain.

**Why it's bad**:
- Merge conflicts when multiple developers work on different features
- Hard to find specific endpoints
- Testing becomes difficult (can't test routes in isolation)
- Can't disable/enable feature groups easily

**Impact**: 🔴 High - Will become unmaintainable with growth

**Fix**:
```
app/routes/
├── __init__.py
├── auth.py              ✅ (already exists)
├── analysis.py          ❌ (needs creation - 5 endpoints)
├── reports.py           ❌ (needs creation - 4 endpoints)
├── intelligence.py      ❌ (needs creation - 2 endpoints)
├── chat.py              ❌ (needs creation - 3 endpoints)
└── admin.py             ❌ (needs creation - 4 endpoints)
```

**Example refactor**:
```python
# app/routes/analysis.py
from fastapi import APIRouter, Depends, BackgroundTasks
from app.models.analysis import AnalysisRequest, AnalysisResponse
from app.services.analysis.multistage import generate_multistage_analysis

router = APIRouter(prefix="/api/analysis", tags=["analysis"])

@router.post("/", response_model=AnalysisResponse)
async def create_analysis(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user)
):
    # ... endpoint logic
    pass

# app/main.py
from app.routes import analysis, reports, intelligence, chat, admin

app.include_router(analysis.router)
app.include_router(reports.router)
# ... etc
```

---

#### 2. **Single models/schemas.py (288 lines)**
**Problem**: All Pydantic models in one file - will grow to 1000+ lines.

**Why it's bad**:
- Hard to find specific models
- Import clutter: `from app.models.schemas import Model1, Model2, Model3, ...`
- Can't organize by domain
- Circular import risks increase

**Impact**: 🟡 Medium - Will slow development as models grow

**Fix**:
```
app/models/
├── __init__.py          # Re-export all models for convenience
├── base.py              # Base models, shared utilities
├── auth.py              # LoginRequest, SignupRequest, TokenResponse
├── analysis.py          # AnalysisRequest, AnalysisResponse, Submission
├── reports.py           # EditRequest, RegeneratePDFResponse
├── intelligence.py      # DashboardIntelligenceRequest
└── enums.py             # Status enums, Industry enums, etc.
```

**Example**:
```python
# app/models/__init__.py (convenience re-exports)
from app.models.auth import LoginRequest, SignupRequest, TokenResponse
from app.models.analysis import AnalysisRequest, AnalysisResponse
# ... etc

# Other files can still do:
from app.models import LoginRequest, AnalysisRequest  # Clean!
```

---

#### 3. **No Centralized Configuration (11 files with os.getenv)**
**Problem**: Environment variables scattered across 11 files, no type safety.

**Why it's bad**:
- Same env var read multiple times (inefficient, inconsistent)
- No validation (typos crash at runtime, not startup)
- Hard to document what env vars are needed
- Can't easily override config for testing

**Impact**: 🔴 High - Production bugs, hard to test, security risks

**Files with scattered config**:
- `app/main.py`, `app/core/supabase.py`, `app/routes/auth.py`
- `app/core/security/rate_limiter.py`
- `app/services/*/*.py` (7 files)

**Fix**:
```python
# app/core/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    """Type-safe, validated configuration"""

    # API
    environment: str = "production"
    allowed_origins: list[str] = []

    # Database
    supabase_url: str
    supabase_service_key: str
    supabase_anon_key: str

    # AI Services
    openrouter_api_key: str
    perplexity_api_key: str | None = None

    # Caching
    upstash_redis_rest_url: str
    upstash_redis_rest_token: str

    # Security
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 10080

    # Rate Limiting
    max_submissions_per_ip_per_day: int = 3

    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton"""
    return Settings()

# Usage anywhere:
from app.core.config import get_settings
settings = get_settings()
print(settings.supabase_url)  # Type-safe, validated!
```

**Benefits**:
- ✅ All config in ONE place
- ✅ Type checking (IDE autocomplete)
- ✅ Validation at startup (fails fast)
- ✅ Easy to mock for tests
- ✅ Self-documenting (see all required env vars)

---

### 🟡 MEDIUM PRIORITY ISSUES

#### 4. **No Repository/DAO Layer**
**Problem**: Services directly call Supabase client everywhere.

**Why it's bad**:
- Can't swap database (tight coupling to Supabase)
- Hard to test (must mock Supabase client)
- Business logic mixed with database queries
- Can't add caching layer easily

**Impact**: 🟡 Medium - Hard to test, hard to migrate

**Current pattern**:
```python
# app/services/analysis/multistage.py (BAD)
from app.core.supabase import supabase_service
result = supabase_service.table("submissions").select("*").execute()
```

**Better pattern**:
```python
# app/repositories/submission.py
class SubmissionRepository:
    def __init__(self, db: SupabaseClient):
        self.db = db

    async def find_by_id(self, submission_id: int) -> Submission | None:
        result = self.db.table("submissions").select("*").eq("id", submission_id).execute()
        return Submission(**result.data[0]) if result.data else None

    async def update_status(self, submission_id: int, status: str) -> None:
        self.db.table("submissions").update({"status": status}).eq("id", submission_id).execute()

# app/services/analysis/multistage.py (GOOD)
from app.repositories.submission import SubmissionRepository

class AnalysisService:
    def __init__(self, repo: SubmissionRepository):
        self.repo = repo

    async def process(self, submission_id: int):
        submission = await self.repo.find_by_id(submission_id)
        # ... business logic
        await self.repo.update_status(submission_id, "completed")
```

**Benefits**:
- ✅ Easy to test (mock repository)
- ✅ Database-agnostic business logic
- ✅ Can add caching in repository
- ✅ Cleaner separation of concerns

---

#### 5. **No Custom Exceptions/Error Handling**
**Problem**: Using generic `HTTPException` everywhere, no centralized error handling.

**Why it's bad**:
- Inconsistent error responses
- Can't add logging/monitoring easily
- Hard to handle errors differently by type
- No business domain exceptions

**Impact**: 🟡 Medium - Poor error UX, hard to debug

**Fix**:
```python
# app/core/exceptions.py
class AppException(Exception):
    """Base exception"""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)

class RateLimitExceeded(AppException):
    def __init__(self):
        super().__init__("Rate limit exceeded", status_code=429)

class AnalysisNotFound(AppException):
    def __init__(self, submission_id: int):
        super().__init__(f"Analysis {submission_id} not found", status_code=404)

class InsufficientData(AppException):
    def __init__(self, reason: str):
        super().__init__(f"Insufficient data: {reason}", status_code=422)

# app/core/middleware.py
from fastapi import Request, status
from fastapi.responses import JSONResponse

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    logger.error(f"AppException: {exc.message}", extra={
        "path": request.url.path,
        "status_code": exc.status_code
    })
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": exc.message}
    )

# Usage:
if not submission:
    raise AnalysisNotFound(submission_id)  # Clean, typed, logged!
```

---

#### 6. **No API Versioning**
**Problem**: No version prefix on routes (e.g., `/api/v1/`).

**Why it's bad**:
- Can't introduce breaking changes without breaking clients
- No migration path for frontend
- Forces you to maintain backward compatibility forever

**Impact**: 🟡 Medium - Future breaking changes will be painful

**Fix**:
```python
# app/routes/v1/analysis.py
router = APIRouter(prefix="/api/v1/analysis")

# app/routes/v2/analysis.py (future)
router = APIRouter(prefix="/api/v2/analysis")

# app/main.py
from app.routes.v1 import analysis as analysis_v1
from app.routes.v2 import analysis as analysis_v2

app.include_router(analysis_v1.router)
app.include_router(analysis_v2.router)
```

---

### 🟢 NICE-TO-HAVE IMPROVEMENTS

#### 7. **Test Structure Doesn't Mirror App Structure**
**Problem**: Flat `tests/` directory instead of mirroring `app/` structure.

**Impact**: 🟢 Low - Minor inconvenience

**Current**:
```
tests/
├── __init__.py
├── test_ai_editor.py
├── test_prompt_injection.py
└── test_submission.json
```

**Better**:
```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── unit/                    # Unit tests
│   ├── services/
│   │   ├── test_analysis.py
│   │   └── test_ai_editor.py
│   ├── core/
│   │   └── test_config.py
│   └── models/
│       └── test_schemas.py
├── integration/             # Integration tests
│   ├── test_analysis_flow.py
│   └── test_database.py
└── e2e/                     # End-to-end tests
    └── test_submission_flow.py
```

---

#### 8. **No Dependency Injection Container**
**Problem**: Dependencies (DB, cache, config) imported globally, not injected.

**Impact**: 🟢 Low - But makes testing harder

**Current**:
```python
from app.core.supabase import supabase_service  # Global import

def my_function():
    supabase_service.table("submissions").select("*")  # Hard to mock!
```

**Better with FastAPI Depends**:
```python
from fastapi import Depends
from app.core.dependencies import get_db

def my_function(db = Depends(get_db)):
    db.table("submissions").select("*")  # Easy to mock in tests!
```

---

#### 9. **No Background Task Queue**
**Problem**: Using FastAPI `BackgroundTasks` for long-running jobs (analysis).

**Why it's bad**:
- Tasks lost if server restarts
- No retry mechanism
- No monitoring/observability
- Can't scale workers independently

**Impact**: 🟢 Low (current scale) → 🔴 High (future scale)

**Future solution** (when needed):
- Celery + Redis for task queue
- Or: Temporal.io for complex workflows
- Or: AWS SQS + Lambda

---

## Recommended Action Plan

### Phase 1: Critical Fixes (2-3 days)
**Prevents immediate pain**

1. ✅ **Split routes** (`main.py` → 6 route files)
   - Priority: HIGH
   - Impact: Massive readability improvement
   - Effort: 4 hours

2. ✅ **Centralize config** (`app/core/config.py`)
   - Priority: HIGH
   - Impact: Prevents prod bugs, easier testing
   - Effort: 2 hours

3. ✅ **Add custom exceptions** (`app/core/exceptions.py`)
   - Priority: MEDIUM
   - Impact: Better error handling, monitoring
   - Effort: 2 hours

### Phase 2: Architecture Improvements (1 week)
**Sets foundation for scaling**

4. ✅ **Split models** (`models/schemas.py` → 5 files)
   - Priority: MEDIUM
   - Impact: Better organization
   - Effort: 3 hours

5. ✅ **Add repository layer** (`app/repositories/`)
   - Priority: MEDIUM
   - Impact: Testability, flexibility
   - Effort: 6 hours

6. ✅ **API versioning** (`/api/v1/` prefix)
   - Priority: MEDIUM
   - Impact: Future-proofing
   - Effort: 2 hours

### Phase 3: Polish (Ongoing)
**Quality of life**

7. ✅ **Reorganize tests** (mirror app structure)
   - Priority: LOW
   - Impact: Minor convenience
   - Effort: 2 hours

8. ✅ **Dependency injection** (consistent use of `Depends()`)
   - Priority: LOW
   - Impact: Better tests
   - Effort: 4 hours

---

## Summary: Will You Regret Current Architecture?

**Yes, you will regret these specific things**:

1. 🔴 **1,834-line main.py** - Guaranteed pain within 1-2 months
2. 🔴 **No centralized config** - Will cause prod bugs
3. 🟡 **No repository layer** - Makes testing painful
4. 🟡 **No API versioning** - Future breaking changes hurt

**You won't regret**:
- ✅ Service separation is good
- ✅ Domain grouping (analysis/, ai/, data/) is excellent
- ✅ Security utilities properly separated

**ROI Estimate**:
- Invest 3 days now (Phase 1 + 2)
- Save 2-3 weeks over next 6 months
- Enable 2-3x faster feature development

---

## Immediate Next Steps

Want me to implement Phase 1 (Critical Fixes) right now?

1. Split main.py into 6 route files
2. Create centralized config
3. Add custom exceptions

This will take ~2 hours and prevent 90% of future pain.
