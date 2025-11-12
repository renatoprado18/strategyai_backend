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
from app.services.enrichment.sources.metadata_enhanced import EnhancedMetadataSource
from app.services.enrichment.sources.ip_api import IpApiSource
from app.services.enrichment.sources.clearbit import ClearbitSource
from app.services.enrichment.sources.receita_ws import ReceitaWSSource
from app.services.enrichment.sources.google_places import GooglePlacesSource
from app.services.enrichment.sources.proxycurl import ProxycurlSource
from app.services.enrichment.sources.ai_inference_enhanced import EnhancedAIInferenceSource
from app.services.enrichment.cache import EnrichmentCache
from app.services.enrichment.intelligent_orchestrator import IntelligentSourceOrchestrator
from app.services.enrichment.confidence_scorer import calculate_confidence_for_session
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
    started_at: Optional[datetime] = None  # Session start timestamp


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
        # Layer 1 sources (free, instant) - ENHANCED
        self.metadata_source = EnhancedMetadataSource()  # Enhanced with social media + structured data
        self.ip_api_source = IpApiSource()

        # Layer 2 sources (paid, parallel)
        self.clearbit_source = ClearbitSource()
        self.receita_ws_source = ReceitaWSSource()
        self.google_places_source = GooglePlacesSource()

        # Layer 3 sources (AI + LinkedIn) - ENHANCED
        self.proxycurl_source = ProxycurlSource()
        self.ai_inference_source = EnhancedAIInferenceSource()  # Enhanced structured AI

        # Intelligence systems
        self.intelligent_orchestrator = IntelligentSourceOrchestrator()

        # Cache
        self.cache = EnrichmentCache(ttl_days=30)

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
        Execute progressive 3-layer enrichment - BULLETPROOF VERSION

        This function NEVER raises exceptions. It always returns a session
        with status "complete", even if all layers fail.

        Args:
            website_url: Company website URL
            user_email: User's email (optional)
            existing_data: Data already collected from user (optional)

        Returns:
            ProgressiveEnrichmentSession with all layer results (may be empty data)

        Flow:
            1. Check cache
            2. Execute Layer 1 (metadata + IP) → return immediately
            3. Execute Layer 2 (Clearbit + ReceitaWS + Google) → return
            4. Execute Layer 3 (AI inference + Proxycurl) → return final

        Error Handling:
            - Each layer wrapped in try/except
            - Layer failures return empty data but continue
            - Always returns "complete" status, never "error"
        """
        import uuid

        session_id = str(uuid.uuid4())
        start_time = datetime.now()

        try:
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

        except Exception as e:
            # Even initialization failed - return minimal session
            logger.error(f"Failed to initialize enrichment session: {e}", exc_info=True)
            return ProgressiveEnrichmentSession(
                session_id=session_id,
                website_url=website_url,
                user_email=user_email,
                status="complete",  # Complete with no data
                total_duration_ms=0,
                total_cost_usd=0.0,
                fields_auto_filled={},
                confidence_scores={}
            )

        # NOTE: Cache check disabled for progressive enrichment
        # Progressive enrichment needs real-time updates via SSE
        # Caching would skip layers and break the progressive UX
        # TODO: Re-enable once we have proper progressive cache invalidation

        # ====================================================================
        # LAYER 1: INSTANT DATA (<2s)
        # ====================================================================

        layer1_start = datetime.now()
        layer1_data = {}
        layer1_sources = []
        layer1_cost = 0.0

        try:
            layer1_tasks = [
                self.metadata_source.enrich(domain),
                self.ip_api_source.enrich(domain)
            ]

            layer1_results = await asyncio.gather(*layer1_tasks, return_exceptions=True)

            # Process Layer 1 results
            for result in layer1_results:
                if isinstance(result, Exception):
                    logger.warning(f"Layer 1 source failed (continuing anyway): {result}", exc_info=True)
                    continue

                if result.success:
                    layer1_data.update(result.data)
                    layer1_sources.append(result.source_name)
                    layer1_cost += result.cost_usd

        except Exception as e:
            logger.error(f"Layer 1 failed completely (continuing with empty data): {e}", exc_info=True)
            # Continue with empty data - Layer 2 can still work

        layer1_duration = int((datetime.now() - layer1_start).total_seconds() * 1000)

        session.layer1_result = LayerResult(
            layer_number=1,
            completed_at=datetime.now(),
            duration_ms=layer1_duration,
            fields_populated=list(layer1_data.keys()),
            data=layer1_data,
            sources_called=layer1_sources,
            cost_usd=layer1_cost,
            confidence_avg=await self._calculate_avg_confidence(layer1_data)
        )

        session.status = "layer1_complete"
        session.total_cost_usd += layer1_cost

        logger.info(f"Layer 1 complete in {layer1_duration}ms: {len(layer1_data)} fields")

        # Update auto-fill suggestions from Layer 1
        try:
            await self._update_auto_fill_suggestions(session, layer1_data, "Layer1", confidence_threshold=70)
        except Exception as e:
            logger.warning(f"Failed to update auto-fill suggestions from Layer 1: {e}")

        # ====================================================================
        # LAYER 2: STRUCTURED DATA (3-6s)
        # ====================================================================

        layer2_start = datetime.now()
        layer2_data = {}
        layer2_sources = []
        layer2_cost = 0.0

        try:
            # Prepare parameters for Layer 2 sources
            company_name = layer1_data.get("company_name")
            location = layer1_data.get("location")

            layer2_tasks = [
                self.clearbit_source.enrich(domain),
                self.receita_ws_source.enrich(domain, company_name=company_name) if company_name else self._empty_result(),
                self.google_places_source.enrich(domain, company_name=company_name, city=location) if company_name else self._empty_result()
            ]

            layer2_results = await asyncio.gather(*layer2_tasks, return_exceptions=True)

            # Process Layer 2 results
            for result in layer2_results:
                if isinstance(result, Exception):
                    logger.warning(f"Layer 2 source failed (continuing anyway): {result}", exc_info=True)
                    continue

                if result.success:
                    layer2_data.update(result.data)
                    layer2_sources.append(result.source_name)
                    layer2_cost += result.cost_usd

        except Exception as e:
            logger.error(f"Layer 2 failed completely (continuing with empty data): {e}", exc_info=True)
            # Continue with empty data - Layer 3 can still work

        layer2_duration = int((datetime.now() - layer2_start).total_seconds() * 1000)

        session.layer2_result = LayerResult(
            layer_number=2,
            completed_at=datetime.now(),
            duration_ms=layer2_duration,
            fields_populated=list(layer2_data.keys()),
            data=layer2_data,
            sources_called=layer2_sources,
            cost_usd=layer2_cost,
            confidence_avg=await self._calculate_avg_confidence(layer2_data)
        )

        session.status = "layer2_complete"
        session.total_cost_usd += layer2_cost

        logger.info(f"Layer 2 complete in {layer2_duration}ms: {len(layer2_data)} fields")

        # Update auto-fill suggestions from Layer 2
        try:
            await self._update_auto_fill_suggestions(session, layer2_data, "Layer2", confidence_threshold=85)
        except Exception as e:
            logger.warning(f"Failed to update auto-fill suggestions from Layer 2: {e}")

        # ====================================================================
        # LAYER 3: AI INFERENCE + LINKEDIN (6-10s) - ENHANCED
        # ====================================================================

        layer3_start = datetime.now()
        layer3_data = {}
        layer3_sources = []
        layer3_cost = 0.0

        try:
            # Combine data for AI inference
            all_data_so_far = {**layer1_data, **layer2_data, **(existing_data or {})}

            # Enhanced AI inference with structured extraction
            layer3_tasks = []

            # Task 1: Enhanced AI inference with strategic insights
            try:
                layer3_tasks.append(
                    self.ai_inference_source.enrich(
                        domain=domain,
                        website_url=website_url,
                        scraped_metadata=layer1_data,
                        layer1_data=layer1_data,
                        layer2_data=layer2_data
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to prepare AI inference (continuing anyway): {e}")

            # Task 2: Proxycurl (LinkedIn enrichment) if we have company name
            try:
                linkedin_url = existing_data.get("linkedin_company") if existing_data else None
                if linkedin_url or company_name:
                    layer3_tasks.append(
                        self.proxycurl_source.enrich(domain, linkedin_url=linkedin_url, company_name=company_name)
                    )
            except Exception as e:
                logger.warning(f"Failed to prepare Proxycurl enrichment (continuing anyway): {e}")

            if layer3_tasks:
                layer3_results = await asyncio.gather(*layer3_tasks, return_exceptions=True)

                # Process Layer 3 results
                for i, result in enumerate(layer3_results):
                    if isinstance(result, Exception):
                        logger.warning(f"Layer 3 source {i} failed (continuing anyway): {result}", exc_info=True)
                        continue

                    if hasattr(result, "success") and result.success:
                        try:
                            layer3_data.update(result.data)
                            layer3_sources.append(result.source_name)
                            layer3_cost += result.cost_usd
                        except Exception as e:
                            logger.warning(f"Failed to process Layer 3 data (skipping): {e}")

        except Exception as e:
            logger.error(f"Layer 3 failed completely (returning partial data): {e}", exc_info=True)
            # Continue with whatever data we have

        layer3_duration = int((datetime.now() - layer3_start).total_seconds() * 1000)

        session.layer3_result = LayerResult(
            layer_number=3,
            completed_at=datetime.now(),
            duration_ms=layer3_duration,
            fields_populated=list(layer3_data.keys()),
            data=layer3_data,
            sources_called=layer3_sources,
            cost_usd=layer3_cost,
            confidence_avg=await self._calculate_avg_confidence(layer3_data)
        )

        session.status = "complete"  # ALWAYS complete, never error
        session.total_cost_usd += layer3_cost
        session.total_duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        logger.info(f"Layer 3 complete in {layer3_duration}ms: {len(layer3_data)} fields")
        logger.info(
            f"Progressive enrichment complete: {session.total_duration_ms}ms, "
            f"${session.total_cost_usd:.4f}"
        )

        # Update auto-fill suggestions from Layer 3
        try:
            await self._update_auto_fill_suggestions(session, layer3_data, "Layer3", confidence_threshold=75)
        except Exception as e:
            logger.warning(f"Failed to update auto-fill suggestions from Layer 3: {e}")

        # ====================================================================
        # CALCULATE CONFIDENCE SCORES
        # ====================================================================
        try:
            field_confidences, overall_confidence = calculate_confidence_for_session(
                layer1_data=layer1_data,
                layer2_data=layer2_data,
                layer3_data=layer3_data,
                layer1_sources=layer1_sources,
                layer2_sources=layer2_sources,
                layer3_sources=layer3_sources
            )

            # Add confidence metadata to session
            session.confidence_scores = field_confidences

            logger.info(
                f"Calculated confidence scores: overall={overall_confidence:.2f}%, "
                f"fields={len(field_confidences)}"
            )

        except Exception as e:
            logger.warning(f"Failed to calculate confidence scores (non-critical): {e}")

        # Cache the complete result (30-day TTL) - skip if caching fails
        try:
            cache_key = f"progressive_enrichment:{domain}"
            await self._cache_session(cache_key, session)
        except Exception as e:
            logger.warning(f"Failed to cache enrichment session (non-critical): {e}")

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

        Note: ML learning system disabled - requires SQLAlchemy to Supabase rewrite
        """
        # ML learning system disabled - gracefully skip
        logger.debug(
            f"ML learning disabled - skipping auto-fill suggestion storage for {field_name}"
        )
        return

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
            Confidence score (0-100) - uses base confidence only (ML learning disabled)

        Note: ML learning system disabled - requires SQLAlchemy to Supabase rewrite
        """
        # ML learning disabled - use base confidence only
        base_confidence = self._get_base_confidence(field)
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

    async def _calculate_avg_confidence(self, data: Dict[str, Any]) -> float:
        """Calculate average confidence for dataset"""
        if not data:
            return 0.0

        # Collect confidence scores with proper async/await
        confidences = []
        for field, value in data.items():
            if value is not None:
                conf = await self._estimate_field_confidence(field, value)
                confidences.append(conf)

        return sum(confidences) / len(confidences) if confidences else 0.0

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

    def _serialize_layer_data(self, layer_result) -> Optional[dict]:
        """
        Serialize layer result with datetime conversion to ISO format.

        Args:
            layer_result: QuickEnrichmentData or DeepEnrichmentData

        Returns:
            Dictionary with all datetime fields converted to ISO strings
        """
        if not layer_result:
            return None

        # Convert to dict
        data = layer_result.dict()

        # Convert all datetime fields to ISO strings
        datetime_fields = [
            'quick_completed_at',
            'deep_completed_at',
            'created_at',
            'updated_at'
        ]

        for field in datetime_fields:
            if field in data and data[field] is not None:
                if isinstance(data[field], datetime):
                    data[field] = data[field].isoformat()

        return data

    async def _cache_session(self, cache_key: str, session: ProgressiveEnrichmentSession):
        """
        Cache complete progressive enrichment session for 30 days.

        Note: Currently stores in database via direct Supabase call since
        EnrichmentCache.set_quick/set_deep are designed for single enrichment types.
        Progressive sessions contain multiple layers of data.
        """
        try:
            # Serialize layer results with datetime conversion
            cache_data = {
                "layer1": self._serialize_layer_data(session.layer1_result),
                "layer2": self._serialize_layer_data(session.layer2_result),
                "layer3": self._serialize_layer_data(session.layer3_result),
                "fields_auto_filled": session.fields_auto_filled,
                "confidence_scores": session.confidence_scores,
                "total_duration_ms": session.total_duration_ms,
                "total_cost_usd": session.total_cost_usd,
                "status": session.status
            }

            expires_at = datetime.now() + timedelta(days=30)

            # Store progressive session in database
            await supabase_service.table("enrichment_sessions").upsert(
                {
                    "cache_key": cache_key,
                    "session_id": session.session_id,
                    "website_url": session.website_url,
                    "user_email": session.user_email,
                    "session_data": cache_data,
                    "total_cost_usd": session.total_cost_usd,
                    "total_duration_ms": session.total_duration_ms,
                    "status": session.status,
                    "expires_at": expires_at.isoformat(),
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                },
                on_conflict="cache_key",
            ).execute()

            logger.info(
                f"Cached progressive enrichment session: {cache_key}",
                extra={
                    "session_id": session.session_id,
                    "cost": session.total_cost_usd,
                    "duration_ms": session.total_duration_ms,
                    "expires_at": expires_at.isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Failed to cache progressive session: {e}", exc_info=True)
            raise
