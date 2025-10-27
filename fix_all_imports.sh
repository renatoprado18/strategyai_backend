#!/bin/bash

# Function to fix imports in a file
fix_file() {
    local file=$1
    echo "Fixing imports in $file"
    
    # Core imports
    sed -i 's/from database import/from app.core.database import/g' "$file"
    sed -i 's/from supabase_client import/from app.core.supabase import/g' "$file"
    sed -i 's/from enhanced_cache import/from app.core.cache import/g' "$file"
    sed -i 's/import enhanced_cache/import app.core.cache as enhanced_cache/g' "$file"
    
    # Models
    sed -i 's/from models import/from app.models.schemas import/g' "$file"
    
    # Security
    sed -i 's/from rate_limiter import/from app.core.security.rate_limiter import/g' "$file"
    sed -i 's/from prompt_injection_sanitizer import/from app.core.security.prompt_sanitizer import/g' "$file"
    sed -i 's/from hallucination_detector import/from app.core.security.hallucination_detector import/g' "$file"
    
    # Services - Analysis
    sed -i 's/from analysis_enhanced import/from app.services.analysis.enhanced import/g' "$file"
    sed -i 's/from analysis_multistage import/from app.services.analysis.multistage import/g' "$file"
    sed -i 's/from industry_deep_dive import/from app.services.analysis.deep_dive import/g' "$file"
    sed -i 's/from confidence_scorer import/from app.services.analysis.confidence_scorer import/g' "$file"
    
    # Services - AI
    sed -i 's/from ai_chat import/from app.services.ai.chat import/g' "$file"
    sed -i 's/from ai_editor import/from app.services.ai.editor import/g' "$file"
    sed -i 's/from adaptive_routing import/from app.services.ai.routing import/g' "$file"
    
    # Services - Data
    sed -i 's/from apify_service import/from app.services.data.apify import/g' "$file"
    sed -i 's/from perplexity_service import/from app.services.data.perplexity import/g' "$file"
    sed -i 's/import perplexity_service/import app.services.data.perplexity as perplexity_service/g' "$file"
    
    # Services - Intelligence
    sed -i 's/from dashboard_intelligence import/from app.services.intelligence.dashboard import/g' "$file"
    sed -i 's/from institutional_memory import/from app.services.intelligence.memory import/g' "$file"
    
    # Services - Other
    sed -i 's/from pdf_generator import/from app.services.pdf_generator import/g' "$file"
    sed -i 's/from report_adapter import/from app.services.report_adapter import/g' "$file"
    
    # Utils
    sed -i 's/from validation_utils import/from app.utils.validation import/g' "$file"
    
    # Auth
    sed -i 's/from auth import/from app.routes.auth import/g' "$file"
}

# Fix all Python files in app/
find app/ -name "*.py" -type f | while read file; do
    fix_file "$file"
done

echo "All imports fixed!"
