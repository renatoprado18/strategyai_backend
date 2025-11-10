"""
Progressive Enrichment Orchestrator

Coordinates 3-layer parallel data collection:
- Layer 1 (<2s): Metadata + IP geolocation (free, instant)
- Layer 2 (3-6s): Clearbit + ReceitaWS + Google Places (paid, parallel)
- Layer 3 (6-10s): AI inference + Proxycurl (AI + LinkedIn data)

Each layer returns results progressively to provide instant feedback.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel

from app.services.enrichment.sources.metadata import MetadataSource
from app.services.enrichment.sources.ip_api import IpApiSource
from app.services.enrichment.sources.clearbit import ClearbitSource
from app.services.enrichment.sources.receita_ws import ReceitaWSSource
from app.services.enrichment.sources.google_places import GooglePlacesSource
from app.services.enrichment.sources.proxycurl import ProxycurlSource
from app.services.enrichment.cache import EnrichmentCache
from app.services.ai.openrouter_client import get_openrouter_client
from app.core.supabase import supabase_service

logger = logging.getLogger(__name__)

# Optional Phase 6 ML learning system (requires SQLAlchemy rewrite for Supabase)
try:
    from app.services.enrichment.confidence_learner import ConfidenceLearner
    CONFIDENCE_LEARNER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Phase 6 ML learning disabled: {e}")
    ConfidenceLearner = None
    CONFIDENCE_LEARNER_AVAILABLE = False


# ============================================================================
# PROGRESSIVE ENRICHMENT MODELS
# ============================================================================


class LayerResult(BaseModel):
    """Result from a single enrichment layer"""

    layer_number: int
    completed_at: datetime
    duration_ms: int
    fields_populated: List[str]
    data: Dict[str, Any]
    sources_called: List[str]
    cost_usd: float
    confidence_avg: float


class ProgressiveEnrichmentSession(BaseModel):
    """Progressive enrichment session tracking"""

    session_id: str
    website_url: str
    user_email: Optional[str] = None
    layer1_result: Optional[LayerResult] = None
    layer2_result: Optional[LayerResult] = None
    layer3_result: Optional[LayerResult] = None
    total_duration_ms: int = 0
    total_cost_usd: float = 0.0
    fields_auto_filled: Dict[str, Any] = {}
    confidence_scores: Dict[str, float] = {}
    status: str = "pending"  # pending/layer1_complete/layer2_complete/complete


# ============================================================================
# PROGRESSIVE ORCHESTRATOR
# ============================================================================


class ProgressiveEnrichmentOrchestrator:
    """
    Orchestrates progressive 3-layer enrichment

    Features:
    - Parallel execution within each layer
    - Progressive results (return after each layer)
    - Confidence scoring per field
    - Cost tracking
    - Auto-fill recommendations
    """

    def __init__(self):
        # Layer 1 sources (free, instant)
        self.metadata_source = MetadataSource()
        self.ip_api_source = IpApiSource()

        # Layer 2 sources (paid, parallel)
        self.clearbit_source = ClearbitSource()
        self.receita_ws_source = ReceitaWSSource()
        self.google_places_source = GooglePlacesSource()

        # Layer 3 sources (AI + LinkedIn)
        self.proxycurl_source = ProxycurlSource()

        # Cache
        self.cache = EnrichmentCache(supabase_service)

        # Learning system (optional - Phase 6)
        self.confidence_learner = ConfidenceLearner() if CONFIDENCE_LEARNER_AVAILABLE else None
        if not CONFIDENCE_LEARNER_AVAILABLE:
            logger.info("Phase 6 ML learning disabled - requires SQLAlchemy to Supabase rewrite")

    async def enrich_progressive(
        self,
        website_url: str,
        user_email: Optional[str] = None,
        existing_data: Optional[Dict[str, Any]] = None
    ) -> ProgressiveEnrichmentSession:
        """
        Execute progressive 3-layer enrichment

        Args:
            website_url: Company website URL
            user_email: User's email (optional)
            existing_data: Data already collected from user (optional)

        Returns:
            ProgressiveEnrichmentSession with all layer results

        Flow:
            1. Check cache
            2. Execute Layer 1 (metadata + IP) → return immediately
            3. Execute Layer 2 (Clearbit + ReceitaWS + Google) → return
            4. Execute Layer 3 (AI inference + Proxycurl) → return final
        """
        import uuid

        session_id = str(uuid.uuid4())
        start_time = datetime.now()

        logger.info(f"Starting progressive enrichment: {website_url}")

        # Extract domain
        from urllib.parse import urlparse
        parsed = urlparse(website_url)
        domain = parsed.netloc or parsed.path

        # Initialize session
        session = ProgressiveEnrichmentSession(
            session_id=session_id,
            website_url=website_url,
            user_email=user_email
        )

        # Check cache (quick check for full enrichment)
        cache_key = f"progressive:{domain}"
        cached_data = await self.cache.get(cache_key)

        if cached_data:
            logger.info(f"Cache HIT for progressive enrichment: {domain}")
            # Return cached data immediately (all layers complete)
            session.layer1_result = LayerResult(**cached_data["layer1"])
            session.layer2_result = LayerResult(**cached_data["layer2"])
            session.layer3_result = LayerResult(**cached_data["layer3"])
            session.fields_auto_filled = cached_data["fields_auto_filled"]
            session.confidence_scores = cached_data["confidence_scores"]
            session.status = "complete"
            session.total_cost_usd = 0.0  # Cache hit = free
            return session

        # ====================================================================
        # LAYER 1: INSTANT DATA (<2s)
        # ====================================================================

        layer1_start = datetime.now()

        layer1_tasks = [
            self.metadata_source.enrich(domain),
            self.ip_api_source.enrich(domain)
        ]

        layer1_results = await asyncio.gather(*layer1_tasks, return_exceptions=True)

        # Process Layer 1 results
        layer1_data = {}
        layer1_sources = []
        layer1_cost = 0.0

        for result in layer1_results:
            if isinstance(result, Exception):
                logger.error(f"Layer 1 source failed: {result}")
                continue

            if result.success:
                layer1_data.update(result.data)
                layer1_sources.append(result.source_name)
                layer1_cost += result.cost_usd

        layer1_duration = int((datetime.now() - layer1_start).total_seconds() * 1000)

        session.layer1_result = LayerResult(
            layer_number=1,
            completed_at=datetime.now(),
            duration_ms=layer1_duration,
            fields_populated=list(layer1_data.keys()),
            data=layer1_data,
            sources_called=layer1_sources,
            cost_usd=layer1_cost,
            confidence_avg=self._calculate_avg_confidence(layer1_data)
        )

        session.status = "layer1_complete"
        session.total_cost_usd += layer1_cost

        logger.info(f"Layer 1 complete in {layer1_duration}ms: {len(layer1_data)} fields")

        # Update auto-fill suggestions from Layer 1
        self._update_auto_fill_suggestions(session, layer1_data, confidence_threshold=70)

        # ====================================================================
        # LAYER 2: STRUCTURED DATA (3-6s)
        # ====================================================================

        layer2_start = datetime.now()

        # Prepare parameters for Layer 2 sources
        company_name = layer1_data.get("company_name")
        location = layer1_data.get("location")

        layer2_tasks = [
            self.clearbit_source.enrich(domain),
            self.receita_ws_source.enrich_by_name(company_name) if company_name else self._empty_result(),
            self.google_places_source.enrich(company_name, location) if company_name else self._empty_result()
        ]

        layer2_results = await asyncio.gather(*layer2_tasks, return_exceptions=True)

        # Process Layer 2 results
        layer2_data = {}
        layer2_sources = []
        layer2_cost = 0.0

        for result in layer2_results:
            if isinstance(result, Exception):
                logger.error(f"Layer 2 source failed: {result}")
                continue

            if result.success:
                layer2_data.update(result.data)
                layer2_sources.append(result.source_name)
                layer2_cost += result.cost_usd

        layer2_duration = int((datetime.now() - layer2_start).total_seconds() * 1000)

        session.layer2_result = LayerResult(
            layer_number=2,
            completed_at=datetime.now(),
            duration_ms=layer2_duration,
            fields_populated=list(layer2_data.keys()),
            data=layer2_data,
            sources_called=layer2_sources,
            cost_usd=layer2_cost,
            confidence_avg=self._calculate_avg_confidence(layer2_data)
        )

        session.status = "layer2_complete"
        session.total_cost_usd += layer2_cost

        logger.info(f"Layer 2 complete in {layer2_duration}ms: {len(layer2_data)} fields")

        # Update auto-fill suggestions from Layer 2
        self._update_auto_fill_suggestions(session, layer2_data, confidence_threshold=85)

        # ====================================================================
        # LAYER 3: AI INFERENCE + LINKEDIN (6-10s)
        # ====================================================================

        layer3_start = datetime.now()

        # Combine data for AI inference
        all_data_so_far = {**layer1_data, **layer2_data, **(existing_data or {})}

        # AI inference tasks (gracefully handle if OpenRouter unavailable)
        layer3_tasks = []

        try:
            ai_client = await get_openrouter_client()

            # Task 1: Extract comprehensive company info
            if all_data_so_far and ai_client.client:  # Check if client initialized
                layer3_tasks.append(
                    ai_client.extract_company_info_from_text(
                        website_url=website_url,
                        scraped_metadata=layer1_data,
                        user_description=existing_data.get("description") if existing_data else None
                    )
                )
            else:
                logger.warning("OpenRouter not available - skipping AI inference")
        except Exception as e:
            logger.error(f"Failed to initialize OpenRouter client: {e}")

        # Task 2: Proxycurl (LinkedIn enrichment) if we have company name
        linkedin_url = existing_data.get("linkedin_company") if existing_data else None
        if linkedin_url or company_name:
            layer3_tasks.append(
                self.proxycurl_source.enrich(company_name, linkedin_url)
            )

        layer3_results = await asyncio.gather(*layer3_tasks, return_exceptions=True)

        # Process Layer 3 results
        layer3_data = {}
        layer3_sources = []
        layer3_cost = 0.0

        for i, result in enumerate(layer3_results):
            if isinstance(result, Exception):
                logger.error(f"Layer 3 source {i} failed: {result}")
                continue

            if i == 0:  # AI extraction result
                # Convert AI extraction to dict
                if hasattr(result, "dict"):
                    ai_data = result.dict()
                    layer3_data.update({
                        "ai_industry": ai_data.get("industry"),
                        "ai_company_size": ai_data.get("company_size"),
                        "ai_digital_maturity": ai_data.get("digital_maturity"),
                        "ai_target_audience": ai_data.get("target_audience"),
                        "ai_key_differentiators": ai_data.get("key_differentiators"),
                    })
                    layer3_sources.append("OpenRouter GPT-4o-mini")
                    # AI cost tracked in client
                    layer3_cost += ai_client.total_cost_usd

            elif hasattr(result, "success") and result.success:  # Proxycurl result
                layer3_data.update(result.data)
                layer3_sources.append(result.source_name)
                layer3_cost += result.cost_usd

        layer3_duration = int((datetime.now() - layer3_start).total_seconds() * 1000)

        session.layer3_result = LayerResult(
            layer_number=3,
            completed_at=datetime.now(),
            duration_ms=layer3_duration,
            fields_populated=list(layer3_data.keys()),
            data=layer3_data,
            sources_called=layer3_sources,
            cost_usd=layer3_cost,
            confidence_avg=self._calculate_avg_confidence(layer3_data)
        )

        session.status = "complete"
        session.total_cost_usd += layer3_cost
        session.total_duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        logger.info(f"Layer 3 complete in {layer3_duration}ms: {len(layer3_data)} fields")
        logger.info(
            f"Progressive enrichment complete: {session.total_duration_ms}ms, "
            f"${session.total_cost_usd:.4f}"
        )

        # Update auto-fill suggestions from Layer 3
        self._update_auto_fill_suggestions(session, layer3_data, confidence_threshold=75)

        # Cache the complete result (30-day TTL)
        await self._cache_session(cache_key, session)

        return session

    async def _update_auto_fill_suggestions(
        self,
        session: ProgressiveEnrichmentSession,
        new_data: Dict[str, Any],
        source_name: str,
        confidence_threshold: float = 85.0
    ):
        """
        Update auto-fill suggestions based on new data with learned confidence scores.

        Args:
            session: Current session
            new_data: New data from latest layer
            source_name: Name of the data source
            confidence_threshold: Minimum confidence to auto-fill
        """
        for field, value in new_data.items():
            if value is not None and value != "":
                # Calculate confidence with learning system
                confidence = await self._estimate_field_confidence(
                    field,
                    value,
                    source=source_name
                )

                # Only auto-fill if confidence meets threshold
                if confidence >= confidence_threshold:
                    session.fields_auto_filled[field] = value
                    session.confidence_scores[field] = confidence

                    # Store suggestion in database for tracking
                    await self._store_auto_fill_suggestion(
                        session_id=session.session_id,
                        field_name=field,
                        suggested_value=value,
                        source=source_name,
                        confidence_score=confidence / 100.0  # Convert to 0-1 scale
                    )

    async def _store_auto_fill_suggestion(
        self,
        session_id: str,
        field_name: str,
        suggested_value: Any,
        source: str,
        confidence_score: float
    ):
        """
        Store auto-fill suggestion in database for later edit tracking.

        Args:
            session_id: Enrichment session ID
            field_name: Name of the field
            suggested_value: The auto-filled value
            source: Data source name
            confidence_score: Confidence score (0-1)
        """
        try:
            from app.core.database import get_db
            db = next(get_db())

            query = """
                INSERT INTO auto_fill_suggestions (
                    session_id,
                    field_name,
                    suggested_value,
                    source,
                    confidence_score,
                    was_edited,
                    created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            """

            await db.execute(
                query,
                session_id,
                field_name,
                str(suggested_value),
                source,
                confidence_score,
                False,  # was_edited = False initially
                datetime.utcnow()
            )
            await db.commit()

            logger.debug(
                f"Stored auto-fill suggestion: {field_name}={suggested_value} "
                f"from {source} (confidence: {confidence_score:.2%})"
            )

        except Exception as e:
            logger.warning(f"Could not store auto-fill suggestion: {e}")

    async def _estimate_field_confidence(
        self,
        field: str,
        value: Any,
        source: Optional[str] = None
    ) -> float:
        """
        Estimate confidence for a field value based on source and learned patterns.

        Args:
            field: Field name
            value: Field value
            source: Data source name (optional)

        Returns:
            Confidence score (0-100) adjusted by learning system
        """
        # Base confidence by source type
        base_confidence = self._get_base_confidence(field)

        # If we have source info, check for learned adjustments
        if source:
            try:
                # Query enrichment_source_performance for learned confidence
                from app.core.database import get_db
                db = next(get_db())

                query = """
                    SELECT confidence_score, learned_adjustment
                    FROM enrichment_source_performance
                    WHERE source = $1 AND field_name = $2
                """
                result = await db.execute(query, source, field)
                row = result.fetchone()

                if row and row[0] is not None:
                    learned_confidence = float(row[0]) * 100  # Convert to 0-100 scale
                    logger.debug(
                        f"Using learned confidence for {field}/{source}: "
                        f"{learned_confidence:.1f}% (base: {base_confidence:.1f}%)"
                    )
                    return learned_confidence

            except Exception as e:
                logger.warning(f"Could not fetch learned confidence: {e}")

        return base_confidence

    def _get_base_confidence(self, field: str) -> float:
        """
        Get base confidence score for a field (before learning adjustments).

        Returns:
            Confidence score (0-100)
        """
        # High confidence fields (verified sources)
        if field in ["cnpj", "legal_name", "registration_status"]:
            return 95.0  # ReceitaWS (government data)

        if field in ["place_id", "rating", "reviews_count", "verified_address"]:
            return 90.0  # Google Places (verified)

        if field in ["employee_count", "annual_revenue", "founded_year"]:
            return 85.0  # Clearbit (high quality B2B data)

        if field.startswith("ai_"):
            return 75.0  # AI inference (good but not perfect)

        if field in ["company_name", "description", "website_tech"]:
            return 70.0  # Metadata scraping (self-reported)

        if field in ["ip_location", "timezone"]:
            return 60.0  # IP geolocation (approximate)

        return 50.0  # Default moderate confidence

    def _calculate_avg_confidence(self, data: Dict[str, Any]) -> float:
        """Calculate average confidence for dataset"""
        if not data:
            return 0.0

        total_confidence = sum(
            self._estimate_field_confidence(field, value)
            for field, value in data.items()
            if value is not None
        )

        return total_confidence / len(data)

    async def _empty_result(self):
        """Return empty enrichment result"""
        from app.services.enrichment.base import EnrichmentResult
        return EnrichmentResult(
            success=False,
            source_name="skipped",
            data={},
            cost_usd=0.0,
            duration_ms=0,
            confidence=0.0
        )

    async def _cache_session(self, cache_key: str, session: ProgressiveEnrichmentSession):
        """Cache complete session for 30 days"""
        cache_data = {
            "layer1": session.layer1_result.dict(),
            "layer2": session.layer2_result.dict(),
            "layer3": session.layer3_result.dict(),
            "fields_auto_filled": session.fields_auto_filled,
            "confidence_scores": session.confidence_scores
        }

        await self.cache.set(
            cache_key,
            cache_data,
            ttl_days=30
        )
