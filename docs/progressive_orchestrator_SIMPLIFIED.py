"""
Progressive Enrichment Orchestrator - SIMPLIFIED VERSION

Coordinates 3-layer parallel data collection with clean separation of concerns.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel
from urllib.parse import urlparse

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

# Constants
CACHE_TTL_DAYS = 30
CONFIDENCE_THRESHOLDS = {"layer1": 70, "layer2": 85, "layer3": 75}


# ============================================================================
# MODELS
# ============================================================================


class LayerResult(BaseModel):
    """Result from a single enrichment layer."""
    layer_number: int
    completed_at: datetime
    duration_ms: int
    fields_populated: List[str]
    data: Dict[str, Any]
    sources_called: List[str]
    cost_usd: float
    confidence_avg: float


class ProgressiveEnrichmentSession(BaseModel):
    """Progressive enrichment session tracking."""
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
    status: str = "pending"


# ============================================================================
# LAYER EXECUTOR (extracted from orchestrator)
# ============================================================================


class LayerExecutor:
    """Handles parallel execution of enrichment sources with error handling."""

    @staticmethod
    async def execute_safe(tasks: List, layer_name: str) -> Tuple[Dict, List, float]:
        """Execute layer tasks with automatic error handling."""
        data, sources, cost = {}, [], 0.0

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.warning(f"{layer_name} source failed: {result}")
                continue

            if hasattr(result, 'success') and result.success:
                data.update(result.data)
                sources.append(result.source_name)
                cost += result.cost_usd

        return data, sources, cost


# ============================================================================
# CONFIDENCE SERVICE (extracted from orchestrator)
# ============================================================================


class ConfidenceService:
    """Handles confidence scoring for enriched fields."""

    BASE_CONFIDENCE = {
        "cnpj": 95, "legal_name": 95, "registration_status": 95,
        "place_id": 90, "rating": 90, "reviews_count": 90,
        "employee_count": 85, "annual_revenue": 85, "founded_year": 85,
        "ai_": 75, "company_name": 70, "description": 70,
        "ip_location": 60, "timezone": 60
    }

    @staticmethod
    def get_base_confidence(field: str) -> float:
        """Get base confidence score for a field."""
        for prefix, score in ConfidenceService.BASE_CONFIDENCE.items():
            if field.startswith(prefix):
                return score
        return 50.0

    @staticmethod
    async def calculate_avg_confidence(data: Dict[str, Any]) -> float:
        """Calculate average confidence for dataset."""
        if not data:
            return 0.0

        confidences = [ConfidenceService.get_base_confidence(field)
                       for field, value in data.items() if value is not None]

        return sum(confidences) / len(confidences) if confidences else 0.0


# ============================================================================
# PROGRESSIVE ORCHESTRATOR
# ============================================================================


class ProgressiveEnrichmentOrchestrator:
    """Orchestrates progressive 3-layer enrichment."""

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

        # Services
        self.cache = EnrichmentCache(ttl_days=CACHE_TTL_DAYS)
        self.layer_executor = LayerExecutor()
        self.confidence_service = ConfidenceService()

    async def enrich_progressive(
        self,
        website_url: str,
        user_email: Optional[str] = None,
        existing_data: Optional[Dict[str, Any]] = None
    ) -> ProgressiveEnrichmentSession:
        """Execute progressive 3-layer enrichment (never raises exceptions)."""
        import uuid

        session_id = str(uuid.uuid4())
        start_time = datetime.now()

        session = self._initialize_session(session_id, website_url, user_email)
        domain = self._extract_domain(website_url)

        # Execute layers sequentially (each updates session)
        layer1_result = await self._execute_layer1(domain)
        session = self._update_session(session, layer1_result, "layer1_complete")

        layer2_result = await self._execute_layer2(domain, layer1_result.data)
        session = self._update_session(session, layer2_result, "layer2_complete")

        layer3_result = await self._execute_layer3(
            domain, website_url,
            {**layer1_result.data, **layer2_result.data},
            existing_data
        )
        session = self._update_session(session, layer3_result, "complete")

        # Finalize
        session.total_duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        logger.info(f"Progressive enrichment complete: {session.total_duration_ms}ms, ${session.total_cost_usd:.4f}")

        await self._cache_session(domain, session)
        return session

    # ========================================================================
    # SESSION MANAGEMENT
    # ========================================================================

    def _initialize_session(self, session_id: str, website_url: str, user_email: Optional[str]) -> ProgressiveEnrichmentSession:
        """Initialize new enrichment session."""
        return ProgressiveEnrichmentSession(
            session_id=session_id,
            website_url=website_url,
            user_email=user_email,
            status="pending"
        )

    def _extract_domain(self, website_url: str) -> str:
        """Extract domain from URL."""
        parsed = urlparse(website_url)
        return parsed.netloc or parsed.path

    def _update_session(self, session: ProgressiveEnrichmentSession, layer_result: LayerResult, status: str) -> ProgressiveEnrichmentSession:
        """Update session with layer result."""
        # Update layer result
        if layer_result.layer_number == 1:
            session.layer1_result = layer_result
        elif layer_result.layer_number == 2:
            session.layer2_result = layer_result
        elif layer_result.layer_number == 3:
            session.layer3_result = layer_result

        # Update totals
        session.status = status
        session.total_cost_usd += layer_result.cost_usd

        # Update auto-fill suggestions
        threshold = CONFIDENCE_THRESHOLDS.get(f"layer{layer_result.layer_number}", 75)
        for field, value in layer_result.data.items():
            if value:
                confidence = self.confidence_service.get_base_confidence(field)
                if confidence >= threshold:
                    session.fields_auto_filled[field] = value
                    session.confidence_scores[field] = confidence

        return session

    # ========================================================================
    # LAYER EXECUTION
    # ========================================================================

    async def _execute_layer1(self, domain: str) -> LayerResult:
        """Execute Layer 1: Instant data (<2s)."""
        start_time = datetime.now()

        tasks = [
            self.metadata_source.enrich(domain),
            self.ip_api_source.enrich(domain)
        ]

        data, sources, cost = await self.layer_executor.execute_safe(tasks, "Layer1")
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        logger.info(f"Layer 1 complete in {duration_ms}ms: {len(data)} fields")

        return LayerResult(
            layer_number=1,
            completed_at=datetime.now(),
            duration_ms=duration_ms,
            fields_populated=list(data.keys()),
            data=data,
            sources_called=sources,
            cost_usd=cost,
            confidence_avg=await self.confidence_service.calculate_avg_confidence(data)
        )

    async def _execute_layer2(self, domain: str, layer1_data: Dict[str, Any]) -> LayerResult:
        """Execute Layer 2: Structured data (3-6s)."""
        start_time = datetime.now()

        company_name = layer1_data.get("company_name")
        location = layer1_data.get("location")

        tasks = [
            self.clearbit_source.enrich(domain),
            self.receita_ws_source.enrich(domain, company_name=company_name) if company_name else self._empty_result(),
            self.google_places_source.enrich(domain, company_name=company_name, city=location) if company_name else self._empty_result()
        ]

        data, sources, cost = await self.layer_executor.execute_safe(tasks, "Layer2")
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        logger.info(f"Layer 2 complete in {duration_ms}ms: {len(data)} fields")

        return LayerResult(
            layer_number=2,
            completed_at=datetime.now(),
            duration_ms=duration_ms,
            fields_populated=list(data.keys()),
            data=data,
            sources_called=sources,
            cost_usd=cost,
            confidence_avg=await self.confidence_service.calculate_avg_confidence(data)
        )

    async def _execute_layer3(
        self,
        domain: str,
        website_url: str,
        previous_data: Dict[str, Any],
        existing_data: Optional[Dict[str, Any]]
    ) -> LayerResult:
        """Execute Layer 3: AI inference + LinkedIn (6-10s)."""
        start_time = datetime.now()
        data, sources, cost = {}, [], 0.0

        try:
            # AI inference
            ai_client = await get_openrouter_client()
            if ai_client.client:
                ai_result = await ai_client.extract_company_info_from_text(
                    website_url=website_url,
                    scraped_metadata=previous_data,
                    user_description=existing_data.get("description") if existing_data else None
                )
                if hasattr(ai_result, "dict"):
                    ai_data = ai_result.dict()
                    data.update({
                        "ai_industry": ai_data.get("industry"),
                        "ai_company_size": ai_data.get("company_size"),
                        "ai_digital_maturity": ai_data.get("digital_maturity"),
                        "ai_target_audience": ai_data.get("target_audience"),
                        "ai_key_differentiators": ai_data.get("key_differentiators"),
                    })
                    sources.append("OpenRouter GPT-4o-mini")
                    cost += ai_client.total_cost_usd

            # Proxycurl
            linkedin_url = existing_data.get("linkedin_company") if existing_data else None
            company_name = previous_data.get("company_name")

            if linkedin_url or company_name:
                proxycurl_result = await self.proxycurl_source.enrich(
                    domain, linkedin_url=linkedin_url, company_name=company_name
                )
                if hasattr(proxycurl_result, 'success') and proxycurl_result.success:
                    data.update(proxycurl_result.data)
                    sources.append(proxycurl_result.source_name)
                    cost += proxycurl_result.cost_usd

        except Exception as e:
            logger.warning(f"Layer 3 had issues (returning partial data): {e}")

        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        logger.info(f"Layer 3 complete in {duration_ms}ms: {len(data)} fields")

        return LayerResult(
            layer_number=3,
            completed_at=datetime.now(),
            duration_ms=duration_ms,
            fields_populated=list(data.keys()),
            data=data,
            sources_called=sources,
            cost_usd=cost,
            confidence_avg=await self.confidence_service.calculate_avg_confidence(data)
        )

    # ========================================================================
    # UTILITIES
    # ========================================================================

    async def _empty_result(self):
        """Return empty enrichment result."""
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
        """Cache complete progressive enrichment session."""
        try:
            cache_data = {
                "layer1": session.layer1_result.dict() if session.layer1_result else None,
                "layer2": session.layer2_result.dict() if session.layer2_result else None,
                "layer3": session.layer3_result.dict() if session.layer3_result else None,
                "fields_auto_filled": session.fields_auto_filled,
                "confidence_scores": session.confidence_scores,
                "total_duration_ms": session.total_duration_ms,
                "total_cost_usd": session.total_cost_usd,
                "status": session.status
            }

            expires_at = datetime.now() + timedelta(days=CACHE_TTL_DAYS)

            await supabase_service.table("enrichment_sessions").upsert(
                {
                    "cache_key": f"progressive_enrichment:{cache_key}",
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

            logger.info(f"Cached progressive enrichment session: {cache_key}")
        except Exception as e:
            logger.warning(f"Failed to cache session (non-critical): {e}")
