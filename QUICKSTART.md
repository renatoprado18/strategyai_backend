# Quick Start - Strategy AI Backend

## Setup in 3 Minutes

### 1. Install Dependencies

```bash
# Create and activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

# Install packages
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file:

```env
OPENROUTER_API_KEY=sk-or-v1-YOUR_KEY_HERE
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
```

Get API key: https://openrouter.ai/keys

### 3. Initialize Database

```bash
python database.py
```

Output:
```
✓ Database initialized: database.db
Database setup complete!
```

### 4. Start Server

```bash
python main.py
```

Or with uvicorn:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Output:
```
🚀 Starting Strategy AI Backend...
✓ Database initialized
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Testing the API

### Health Check

```bash
curl http://localhost:8000/
```

Expected:
```json
{
  "service": "Strategy AI Lead Generator API",
  "status": "running",
  "version": "1.0.0"
}
```

### Submit a Lead

```bash
curl -X POST http://localhost:8000/api/submit \
  -H "Content-Type: application/json" \
  -d @test_submission.json
```

Expected:
```json
{
  "success": true,
  "submission_id": 1
}
```

Server logs:
```
⚙️  Processing analysis for submission 1...
✓ Analysis completed for submission 1
```

### View Submissions

```bash
curl http://localhost:8000/api/admin/submissions
```

### View API Docs

Open browser:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Test AI Analysis Standalone

```bash
python analysis.py
```

This tests the OpenRouter integration without the full API.

## Project Structure

```
strategy-ai-backend/
├── main.py              # FastAPI app + endpoints
├── models.py            # Pydantic validation models
├── database.py          # SQLite operations
├── analysis.py          # AI analysis engine
├── requirements.txt     # Dependencies
├── .env                 # Environment variables (create this)
├── database.db          # SQLite file (auto-created)
└── README.md            # Full documentation
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| POST | `/api/submit` | Submit new lead |
| GET | `/api/admin/submissions` | List all submissions |
| POST | `/api/admin/reprocess/{id}` | Reprocess failed submission |

## Environment Variables

| Variable | Required | Default |
|----------|----------|---------|
| `OPENROUTER_API_KEY` | ✅ Yes | - |
| `ALLOWED_ORIGINS` | No | `http://localhost:3000` |
| `MAX_SUBMISSIONS_PER_IP_PER_DAY` | No | `3` |

## Connect to Frontend

Update frontend `.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Then test the full flow:
1. Start backend: `python main.py`
2. Start frontend: `npm run dev` (in frontend directory)
3. Open http://localhost:3000
4. Fill and submit form
5. Check backend logs for analysis progress
6. View admin dashboard: http://localhost:3000/admin/dashboard-x9k2p

## Common Issues

### "OPENROUTER_API_KEY not set"
- Create `.env` file in backend directory
- Add: `OPENROUTER_API_KEY=your_key_here`

### "Module not found"
- Activate virtual environment
- Run: `pip install -r requirements.txt`

### CORS errors in browser
- Add frontend URL to `ALLOWED_ORIGINS` in `.env`
- Restart backend server

### Analysis fails
- Check OpenRouter API key is valid
- Ensure you have credits: https://openrouter.ai/credits
- Check logs for specific error message

## Deploy to Railway

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Set environment variables
railway variables set OPENROUTER_API_KEY=your_key_here
railway variables set ALLOWED_ORIGINS=https://your-frontend.vercel.app

# Deploy
railway up

# Get URL
railway domain
```

Update frontend with Railway URL:
```env
NEXT_PUBLIC_API_URL=https://your-api.railway.app
```

## Next Steps

1. ✅ Test locally with frontend
2. ✅ Get OpenRouter API key with credits
3. ✅ Deploy backend to Railway
4. ✅ Update frontend env variable
5. ✅ Deploy frontend to Vercel
6. ✅ Test production flow end-to-end

## Support

- API Docs: http://localhost:8000/docs
- OpenRouter Status: https://status.openrouter.ai
- Railway Docs: https://docs.railway.app

---

**Status**: Phase 2 Complete ✅ Ready for deployment!
