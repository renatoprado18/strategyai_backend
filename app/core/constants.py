"""
Application Constants and Configuration Values

This module centralizes all hardcoded magic numbers used throughout the application,
organized by domain for easy maintenance and configuration.

All timeout values are in seconds unless otherwise specified.
All token limits are for LLM API calls.
All cache TTLs are in hours unless otherwise specified.
"""

# ============================================================================
# HTTP & SECURITY CONFIGURATION
# ============================================================================

# Request size limits (prevent DoS attacks)
REQUEST_MAX_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB max request size
REQUEST_MAX_SIZE_MB = REQUEST_MAX_SIZE_BYTES / (1024 * 1024)

# File upload limits
UPLOAD_MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB per file
UPLOAD_ALLOWED_EXTENSIONS = [".pdf", ".txt", ".md", ".json", ".csv"]

# ============================================================================
# LLM API CONFIGURATION
# ============================================================================

# Timeout values for LLM API calls (seconds)
LLM_TIMEOUT_DEFAULT = 120.0  # Default timeout for most LLM operations
LLM_TIMEOUT_DASHBOARD = 60.0  # Shorter timeout for dashboard queries (non-critical)
LLM_TIMEOUT_EDITOR = 60.0  # Timeout for AI editor operations

# Retry configuration for LLM calls
LLM_MAX_RETRIES = 3  # Maximum number of retry attempts for failed LLM calls
LLM_RETRY_TEMPERATURE_DECAY = 0.7  # Temperature multiplier on each retry (reduces randomness)

# Token limits per stage/operation
# Stage 1: Data Extraction
STAGE1_MAX_TOKENS = 4000  # Extraction of structured data from sources

# Stage 2: Gap Analysis
STAGE2_MAX_TOKENS_ANALYSIS = 1000  # Gap identification
STAGE2_MAX_TOKENS_FOLLOWUP = 3000  # Follow-up research queries

# Stage 3: Strategic Analysis (MOST EXPENSIVE STAGE)
STAGE3_MAX_TOKENS = 32000  # Increased from 16k to prevent JSON truncation for large frameworks

# Stage 4: Competitive Intelligence
STAGE4_MAX_TOKENS = 4000  # Competitive matrix generation

# Stage 5: Risk Scoring
STAGE5_MAX_TOKENS = 6000  # Risk quantification and prioritization

# Stage 6: Executive Polish
STAGE6_MAX_TOKENS = 10000  # Final polish for executive readability

# Dashboard Intelligence
DASHBOARD_MAX_TOKENS_SUMMARY = 500  # Quick summaries
DASHBOARD_MAX_TOKENS_TRENDS = 1000  # Trend analysis
DASHBOARD_MAX_TOKENS_INSIGHTS = 1500  # Detailed insights
DASHBOARD_MAX_TOKENS_DEFAULT = 2000  # Default for general queries

# AI Editor
EDITOR_MAX_TOKENS = 2000  # Edit suggestions and rewrites

# Perplexity Research
PERPLEXITY_MAX_TOKENS_DEFAULT = 4000  # Standard research queries
PERPLEXITY_MAX_TOKENS_COMPETITORS = 6000  # Deep competitor analysis
PERPLEXITY_MAX_TOKENS_MARKET = 5000  # Market sizing and trends
PERPLEXITY_MAX_TOKENS_COMPANY = 5000  # Company intelligence
PERPLEXITY_MAX_TOKENS_SOLUTIONS = 6000  # Solution strategies
PERPLEXITY_MAX_TOKENS_TEST = 500  # Quick connection test

# LLM Temperature Settings
TEMPERATURE_FACTUAL = 0.3  # Low temperature for factual extraction, consistent output
TEMPERATURE_BALANCED = 0.5  # Moderate temperature for balanced analysis
TEMPERATURE_CREATIVE = 0.8  # Higher temperature for creative strategic thinking
TEMPERATURE_DETERMINISTIC = 0.4  # Very low for deterministic, repeatable results


# ============================================================================
# CIRCUIT BREAKER CONFIGURATION
# ============================================================================

# Circuit breaker thresholds (number of failures before opening circuit)
CIRCUIT_BREAKER_FAILURE_THRESHOLD_DEFAULT = 5  # Default failure threshold
CIRCUIT_BREAKER_FAILURE_THRESHOLD_APIFY = 3  # Lower threshold for scraping (often flaky)
CIRCUIT_BREAKER_FAILURE_THRESHOLD_SUPABASE = 10  # Higher threshold for database (more stable)

# Circuit breaker success thresholds (successes needed in half-open state to close circuit)
CIRCUIT_BREAKER_SUCCESS_THRESHOLD = 2  # Default successes needed to close circuit

# Circuit breaker timeouts (seconds before transitioning from OPEN to HALF_OPEN)
CIRCUIT_BREAKER_TIMEOUT_DEFAULT = 60  # 1 minute - standard recovery time
CIRCUIT_BREAKER_TIMEOUT_APIFY = 120  # 2 minutes - longer timeout for scraping operations
CIRCUIT_BREAKER_TIMEOUT_SUPABASE = 30  # 30 seconds - database usually recovers quickly


# ============================================================================
# CACHE TTL CONFIGURATION (Time-To-Live in hours)
# ============================================================================

# Analysis result caching (aggressive - saves $15-25 per hit!)
CACHE_TTL_ANALYSIS = 24 * 30  # 30 days (720 hours) - complete analysis cache
CACHE_TTL_STAGE = 24 * 7  # 7 days (168 hours) - individual pipeline stage cache
CACHE_TTL_PDF = 24 * 90  # 90 days (2160 hours) - PDF cache (cheap to store)
CACHE_TTL_STATS = 1/12  # 5 minutes (0.083 hours) - dashboard stats cache
CACHE_TTL_PERPLEXITY = 24 * 14  # 14 days (336 hours) - Perplexity research cache

# Cache size limits
CACHE_MAX_PDFS_IN_MEMORY = 50  # Maximum number of PDFs to keep in memory (~100-250MB)


# ============================================================================
# PIPELINE STAGE COST ESTIMATES (USD)
# ============================================================================

# Estimated cost per stage (for cache savings tracking)
COST_ESTIMATE_STAGE1 = 0.002  # ~$0.002 per Stage 1 call (extraction)
COST_ESTIMATE_STAGE2 = 0.005  # ~$0.005 per Stage 2 call (gap analysis + Perplexity)
COST_ESTIMATE_STAGE3 = 0.15  # ~$0.15 per Stage 3 call (MOST EXPENSIVE - strategic frameworks)
COST_ESTIMATE_STAGE4 = 0.05  # ~$0.05 per Stage 4 call (competitive matrix)
COST_ESTIMATE_STAGE5 = 0.04  # ~$0.04 per Stage 5 call (risk scoring)
COST_ESTIMATE_STAGE6 = 0.01  # ~$0.01 per Stage 6 call (polish)


# ============================================================================
# HTTP CLIENT CONFIGURATION
# ============================================================================

# Timeout for external API calls (seconds)
HTTP_TIMEOUT_APIFY = 120  # 120 second timeout for web scraping operations
HTTP_TIMEOUT_PERPLEXITY = 120.0  # 120 second timeout for Perplexity research


# ============================================================================
# APPLICATION LIFECYCLE
# ============================================================================

# Graceful shutdown delays (seconds)
SHUTDOWN_GRACE_PERIOD = 2  # Give active requests time to finish before shutdown


# ============================================================================
# STREAMING AND WEBSOCKET CONFIGURATION
# ============================================================================

# Delays for streaming operations (seconds)
STREAM_FINAL_MESSAGE_DELAY = 1  # Give client time to receive final message before closing
STREAM_ERROR_DELAY = 1  # Delay before closing on error


# ============================================================================
# TESTING CONFIGURATION
# ============================================================================

# Test delays (seconds)
TEST_DELAY_BETWEEN_TESTS = 0.1  # Small delay between smoke tests


# ============================================================================
# TEXT TRUNCATION LIMITS
# ============================================================================

# Maximum length for text fields in cache keys and database
MAX_CHALLENGE_SNIPPET_LENGTH = 50  # First N chars of challenge for cache key
MAX_CHALLENGE_DB_LENGTH = 100  # Challenge snippet stored in database
MAX_RESEARCH_DATA_LENGTH = 3000  # Maximum length for sanitized research data


# ============================================================================
# EDIT COMPLEXITY CLASSIFICATION
# ============================================================================

# Word count thresholds for determining edit complexity
EDIT_SIMPLE_WORD_THRESHOLD = 5  # Instructions with ≤5 words are usually simple
EDIT_COMPLEX_WORD_THRESHOLD = 10  # Instructions with >10 words are usually complex


# ============================================================================
# MODEL CONFIGURATION
# ============================================================================

# Token cost calculation
TOKENS_PER_MILLION = 1_000_000  # Divisor for cost per million tokens calculation

# Typical token usage estimates for cost calculation
TYPICAL_TOKENS_BACKEND_INPUT = 20_000  # Typical input tokens for backend tasks
TYPICAL_TOKENS_BACKEND_OUTPUT = 3_000  # Typical output tokens for backend tasks
TYPICAL_TOKENS_RESEARCH_INPUT = 25_000  # Typical input tokens for research tasks
TYPICAL_TOKENS_RESEARCH_OUTPUT = 3_500  # Typical output tokens for research tasks
TYPICAL_TOKENS_STRATEGIC_INPUT = 30_000  # Typical input tokens for strategic tasks
TYPICAL_TOKENS_STRATEGIC_OUTPUT = 4_000  # Typical output tokens for strategic tasks
TYPICAL_TOKENS_CLIENT_FACING_INPUT = 30_000  # Typical input tokens for client-facing tasks
TYPICAL_TOKENS_CLIENT_FACING_OUTPUT = 4_000  # Typical output tokens for client-facing tasks


# ============================================================================
# HASH AND KEY GENERATION
# ============================================================================

# Hash truncation lengths for cache keys
HASH_LENGTH_SHORT = 16  # Short hash for cache keys (16 hex chars = 64 bits)


# ============================================================================
# PERPLEXITY RESEARCH CONFIGURATION
# ============================================================================

# Research timeframes
PERPLEXITY_COMPANY_INTEL_DAYS = 90  # Days of company intelligence to fetch (last 3 months)
