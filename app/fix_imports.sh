#!/bin/bash

# Fix all imports in main.py
sed -i 's/from models import/from app.models.schemas import/g' main.py
sed -i 's/from database import/from app.core.database import/g' main.py
sed -i 's/from analysis_enhanced import/from app.services.analysis.enhanced import/g' main.py
sed -i 's/from analysis_multistage import/from app.services.analysis.multistage import/g' main.py
sed -i 's/from auth import/from app.routes.auth import/g' main.py
sed -i 's/from rate_limiter import/from app.core.security.rate_limiter import/g' main.py
sed -i 's/from apify_service import/from app.services.data.apify import/g' main.py
sed -i 's/from perplexity_service import/from app.services.data.perplexity import/g' main.py
sed -i 's/import perplexity_service/import app.services.data.perplexity as perplexity_service/g' main.py
sed -i 's/from dashboard_intelligence import/from app.services.intelligence.dashboard import/g' main.py
sed -i 's/from ai_editor import/from app.services.ai.editor import/g' main.py
sed -i 's/from pdf_generator import/from app.services.pdf_generator import/g' main.py
sed -i 's/from confidence_scorer import/from app.services.analysis.confidence_scorer import/g' main.py
sed -i 's/from ai_chat import/from app.services.ai.chat import/g' main.py

echo "Main imports fixed"
