# Phase 7 Implementation Plan: A/B Testing & Recommendations Engine

## Overview

This document provides a tactical, week-by-week implementation plan for Phase 7 of the IMENSIAH enrichment system. Phase 7 introduces A/B testing and automated recommendations to optimize cost-quality balance.

---

## Sprint Breakdown

### Week 1: Database & Infrastructure

#### Day 1-2: Database Schema
**Tasks**:
- [ ] Review `009_ab_testing_and_recommendations.sql` migration
- [ ] Run migration in Supabase SQL editor
- [ ] Verify tables created:
  - `ab_test_variants` (3 sample variants inserted)
  - `ab_test_assignments`
  - `ab_test_results`
  - `recommendations_history`
  - `ab_test_events`
- [ ] Verify views created:
  - `ab_test_variant_performance`
  - `ab_test_winner_analysis`
- [ ] Verify functions created:
  - `assign_ab_test_variant()`
  - `calculate_ab_test_metrics()`
- [ ] Test database functions manually

**Verification Script**:
```sql
-- Test variant assignment
SELECT assign_ab_test_variant('session_123', 1);
SELECT assign_ab_test_variant('session_123', 2);  -- Should return same variant
SELECT assign_ab_test_variant('session_456', 3);  -- Different session = different variant

-- Test metrics calculation
SELECT calculate_ab_test_metrics(
    1,  -- variant_id
    NOW() - INTERVAL '24 hours',
    NOW()
);

-- View aggregated results
SELECT * FROM ab_test_variant_performance;
```

**Deliverables**:
- Migration file executed successfully
- Database verification report
- Sample data in all tables

---

#### Day 3-4: Repository Layer
**Tasks**:
- [ ] Create `app/repositories/ab_test_repository.py`

```python
"""
Repository for A/B testing database operations
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from app.core.database import supabase

class ABTestRepository:
    """Database operations for A/B testing"""

    async def get_active_variants(self) -> List[Dict[str, Any]]:
        """Get all active A/B test variants"""
        response = supabase.table("ab_test_variants")\
            .select("*")\
            .eq("is_active", True)\
            .execute()
        return response.data

    async def get_variant_by_key(self, variant_key: str) -> Optional[Dict[str, Any]]:
        """Get variant by key"""
        response = supabase.table("ab_test_variants")\
            .select("*")\
            .eq("variant_key", variant_key)\
            .single()\
            .execute()
        return response.data if response.data else None

    async def assign_variant(
        self,
        session_id: str,
        enrichment_id: int
    ) -> Optional[str]:
        """Assign A/B test variant using database function"""
        response = supabase.rpc(
            "assign_ab_test_variant",
            {
                "p_session_id": session_id,
                "p_enrichment_id": enrichment_id
            }
        ).execute()
        return response.data

    async def get_variant_performance(self) -> List[Dict[str, Any]]:
        """Get variant performance from view"""
        response = supabase.table("ab_test_variant_performance")\
            .select("*")\
            .execute()
        return response.data

    async def record_event(
        self,
        enrichment_id: int,
        variant_id: int,
        event_type: str,
        event_value: Optional[float] = None,
        event_metadata: Optional[Dict] = None
    ):
        """Record A/B test event"""
        supabase.table("ab_test_events").insert({
            "enrichment_id": enrichment_id,
            "variant_id": variant_id,
            "event_type": event_type,
            "event_value": event_value,
            "event_metadata": event_metadata
        }).execute()

    async def calculate_metrics(
        self,
        variant_id: int,
        time_window_start: datetime,
        time_window_end: datetime
    ):
        """Calculate aggregated metrics for variant"""
        supabase.rpc(
            "calculate_ab_test_metrics",
            {
                "p_variant_id": variant_id,
                "p_time_window_start": time_window_start.isoformat(),
                "p_time_window_end": time_window_end.isoformat()
            }
        ).execute()

    async def create_recommendation(
        self,
        budget_per_enrichment: float,
        min_confidence: float,
        min_completeness: float,
        recommended_variant_id: int,
        recommended_sources: List[str],
        predicted_cost: float,
        predicted_completeness: float,
        predicted_confidence: float,
        prediction_confidence_interval: Dict[str, float],
        recommendation_algorithm: str,
        recommendation_rationale: str
    ) -> int:
        """Create recommendation record"""
        response = supabase.table("recommendations_history").insert({
            "budget_per_enrichment": budget_per_enrichment,
            "min_confidence_required": min_confidence,
            "min_completeness_required": min_completeness,
            "recommended_variant_id": recommended_variant_id,
            "recommended_sources": recommended_sources,
            "predicted_cost": predicted_cost,
            "predicted_completeness": predicted_completeness,
            "predicted_confidence": predicted_confidence,
            "prediction_confidence_interval": prediction_confidence_interval,
            "recommendation_algorithm": recommendation_algorithm,
            "recommendation_rationale": recommendation_rationale
        }).execute()
        return response.data[0]["id"]

    async def get_recommendations_history(
        self,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get recommendation history"""
        response = supabase.table("recommendations_history")\
            .select("*")\
            .order("recommended_at", desc=True)\
            .limit(limit)\
            .execute()
        return response.data
```

**Deliverables**:
- `ABTestRepository` class with full CRUD operations
- Unit tests for repository methods

---

#### Day 5: Variant Assigner Service
**Tasks**:
- [ ] Create `app/services/ab_testing/assigner.py`

```python
"""
Variant assignment logic for A/B testing
"""
from typing import List, Optional
from app.repositories.ab_test_repository import ABTestRepository
import logging

logger = logging.getLogger(__name__)

class VariantAssigner:
    """Assigns A/B test variants to enrichment sessions"""

    def __init__(self):
        self.repo = ABTestRepository()

    async def assign_variant(
        self,
        session_id: str,
        enrichment_id: int
    ) -> str:
        """
        Assign A/B test variant based on session_id hash.

        Uses database function for consistent hashing.
        Same session_id always gets same variant.

        Args:
            session_id: Session identifier (from cookie, IP, or generated)
            enrichment_id: Enrichment record ID

        Returns:
            variant_key: "full_stack", "free_only", or "hybrid"
        """
        variant_key = await self.repo.assign_variant(session_id, enrichment_id)

        if not variant_key:
            logger.warning("No active A/B test variants found, using default")
            variant_key = "full_stack"  # Fallback

        logger.info(
            f"Assigned variant '{variant_key}' to session {session_id}",
            extra={
                "session_id": session_id,
                "enrichment_id": enrichment_id,
                "variant_key": variant_key
            }
        )

        return variant_key

    async def get_variant_sources(self, variant_key: str) -> List[str]:
        """
        Get sources configuration for variant.

        Args:
            variant_key: Variant identifier

        Returns:
            List of source names to use (e.g., ["clearbit", "metadata"])
        """
        variant = await self.repo.get_variant_by_key(variant_key)

        if not variant:
            logger.error(f"Variant '{variant_key}' not found")
            return []

        sources = variant.get("sources_config", [])

        logger.debug(
            f"Variant '{variant_key}' sources: {sources}",
            extra={"variant_key": variant_key, "sources": sources}
        )

        return sources
```

**Deliverables**:
- `VariantAssigner` class
- Unit tests for assignment consistency
- Integration tests with database

---

### Week 2: Orchestrator Integration & Metrics

#### Day 6-7: Orchestrator Modification
**Tasks**:
- [ ] Modify `app/services/enrichment/orchestrator.py` to accept source filtering

```python
# In EnrichmentOrchestrator class

async def enrich_deep(
    self,
    website: str,
    enrichment_id: Optional[int] = None,
    company_name: Optional[str] = None,
    city: Optional[str] = None,
    sources_filter: Optional[List[str]] = None,  # NEW PARAMETER
) -> DeepEnrichmentData:
    """
    ASYNC deep enrichment (30+ seconds).

    NEW: Supports A/B testing by filtering sources.

    Args:
        sources_filter: List of source names to use (for A/B testing)
                       If None, uses all sources
    """
    start_time = time.time()
    domain = self._extract_domain(website)

    logger.info(
        f"Starting DEEP enrichment for: {domain}",
        extra={
            "domain": domain,
            "sources_filter": sources_filter,
            "ab_test_enabled": sources_filter is not None
        }
    )

    # Filter deep sources based on A/B test variant
    active_sources = self.deep_sources
    if sources_filter:
        active_sources = [
            source for source in self.deep_sources
            if source.name in sources_filter
        ]
        logger.info(
            f"A/B test: Using {len(active_sources)}/{len(self.deep_sources)} sources",
            extra={
                "filtered_sources": [s.name for s in active_sources],
                "total_sources": [s.name for s in self.deep_sources]
            }
        )

    # Rest of enrichment logic...
    # (Use active_sources instead of self.deep_sources)
```

**Deliverables**:
- Modified orchestrator with source filtering
- Backward compatibility maintained (sources_filter=None = all sources)
- Unit tests for source filtering

---

#### Day 8-9: Enrichment Route Integration
**Tasks**:
- [ ] Modify `app/routes/enrichment.py` to integrate A/B testing

```python
from app.services.ab_testing.assigner import VariantAssigner

@router.post("/submit")
async def submit_enrichment(
    request: EnrichmentSubmitRequest,
    background_tasks: BackgroundTasks,
    request_obj: Request
):
    """Submit company website for enrichment (with A/B testing)"""

    # Generate or extract session_id
    session_id = request_obj.cookies.get("session_id") or str(uuid.uuid4())

    # Create enrichment record first
    enrichment_id = await enrichment_repo.create(
        email=request.email,
        website=request.company_website
    )

    # Assign A/B test variant
    assigner = VariantAssigner()
    variant_key = await assigner.assign_variant(session_id, enrichment_id)
    sources = await assigner.get_variant_sources(variant_key)

    # Quick enrichment (no filtering needed - always uses free sources)
    orchestrator = EnrichmentOrchestrator()
    quick_data = await orchestrator.enrich_quick(request.company_website)

    # Deep enrichment with A/B test sources
    background_tasks.add_task(
        orchestrator.enrich_deep,
        request.company_website,
        enrichment_id=enrichment_id,
        sources_filter=sources  # Apply A/B test variant
    )

    return {
        "success": True,
        "enrichment_id": enrichment_id,
        "ab_test_variant": variant_key,  # NEW: Inform user of variant
        "data": quick_data.dict(exclude_none=True),
        "message": f"Quick enrichment complete! (Using {variant_key} strategy)"
    }
```

**Deliverables**:
- Modified enrichment submit endpoint
- Session ID management
- A/B variant assignment in response
- Integration tests

---

#### Day 10: Metrics Collection Service
**Tasks**:
- [ ] Create `app/services/ab_testing/metrics.py`

```python
"""
Metrics collection for A/B testing
"""
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from app.repositories.ab_test_repository import ABTestRepository
import logging

logger = logging.getLogger(__name__)

class MetricsCollector:
    """Collects and aggregates A/B test metrics"""

    def __init__(self):
        self.repo = ABTestRepository()

    async def record_event(
        self,
        enrichment_id: int,
        variant_id: int,
        event_type: str,
        event_value: Optional[float] = None,
        event_metadata: Optional[Dict] = None
    ):
        """
        Record A/B test event.

        Event types:
        - "time_to_autofill": How long quick enrichment took (ms)
        - "form_completed": User completed form (value=1)
        - "user_edited": User edited enriched data (value=1)
        - "data_accepted": User accepted data without edits (value=1)
        """
        await self.repo.record_event(
            enrichment_id=enrichment_id,
            variant_id=variant_id,
            event_type=event_type,
            event_value=event_value,
            event_metadata=event_metadata
        )

        logger.info(
            f"Recorded A/B test event: {event_type}",
            extra={
                "enrichment_id": enrichment_id,
                "variant_id": variant_id,
                "event_type": event_type,
                "event_value": event_value
            }
        )

    async def aggregate_metrics(
        self,
        variant_id: int,
        time_window_hours: int = 24
    ):
        """
        Calculate aggregated metrics for variant.

        Calls database function to compute:
        - cost_per_enrichment
        - avg_completeness
        - avg_confidence
        - user_edit_rate
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=time_window_hours)

        await self.repo.calculate_metrics(
            variant_id=variant_id,
            time_window_start=start_time,
            time_window_end=end_time
        )

        logger.info(
            f"Aggregated metrics for variant {variant_id}",
            extra={
                "variant_id": variant_id,
                "time_window_hours": time_window_hours
            }
        )
```

**Deliverables**:
- `MetricsCollector` class
- Event recording in enrichment flow
- Unit tests for metrics collection

---

### Week 3: Recommendations Engine

#### Day 11-13: Recommender Service
**Tasks**:
- [ ] Create `app/services/ab_testing/recommender.py`

```python
"""
Recommendations engine for optimal enrichment strategy
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from app.repositories.ab_test_repository import ABTestRepository
import logging

logger = logging.getLogger(__name__)

class RecommendationStrategy(BaseModel):
    """Recommended enrichment strategy"""
    variant_key: str
    variant_name: str
    sources: List[str]
    predicted_cost: float
    predicted_completeness: float
    predicted_confidence: float
    confidence_interval: Dict[str, float]
    rationale: str
    monthly_cost_projection: float
    alternative_strategies: List[Dict[str, Any]]

class EnrichmentRecommender:
    """Recommends optimal enrichment strategy"""

    def __init__(self):
        self.repo = ABTestRepository()

    async def recommend_strategy(
        self,
        budget_per_enrichment: float,
        min_confidence: float,
        min_completeness: float,
        expected_volume_per_month: int = 1000,
        historical_lookback_days: int = 30
    ) -> RecommendationStrategy:
        """
        Recommend optimal enrichment strategy.

        Algorithm: Pareto optimization
        1. Fetch variant performance data
        2. Filter variants meeting quality constraints
        3. Calculate quality_per_dollar = completeness / cost
        4. Rank by ROI
        5. Return best within budget

        Args:
            budget_per_enrichment: Max cost per enrichment (USD)
            min_confidence: Minimum confidence score required (0-100)
            min_completeness: Minimum completeness score required (0-100)
            expected_volume_per_month: Expected enrichments/month
            historical_lookback_days: Days of data to analyze

        Returns:
            RecommendationStrategy with predicted performance
        """
        # Get variant performance data
        variants = await self.repo.get_variant_performance()

        if not variants:
            logger.warning("No variant performance data available")
            return self._fallback_recommendation()

        # Filter by quality constraints
        candidates = [
            v for v in variants
            if v.get("avg_confidence", 0) >= min_confidence
            and v.get("avg_completeness", 0) >= min_completeness
            and v.get("sample_size", 0) >= 20  # Minimum sample for reliability
        ]

        if not candidates:
            logger.warning(
                f"No variants meet quality constraints "
                f"(confidence>={min_confidence}, completeness>={min_completeness})"
            )
            # Relax constraints
            candidates = variants

        # Calculate ROI (quality per dollar)
        for c in candidates:
            cost = c.get("avg_cost_per_enrichment", 0.001)
            completeness = c.get("avg_completeness", 0)
            c["roi"] = completeness / max(cost, 0.001)  # Avoid division by zero

        # Sort by ROI descending
        candidates.sort(key=lambda x: x.get("roi", 0), reverse=True)

        # Find best within budget
        within_budget = [
            c for c in candidates
            if c.get("avg_cost_per_enrichment", 0) <= budget_per_enrichment
        ]

        if within_budget:
            recommended = within_budget[0]
        else:
            # No variant within budget, recommend cheapest
            recommended = min(candidates, key=lambda x: x.get("avg_cost_per_enrichment", 0))

        # Generate rationale
        rationale = self._generate_rationale(
            recommended,
            budget_per_enrichment,
            min_confidence,
            min_completeness
        )

        # Calculate confidence interval (95%)
        std_dev = recommended.get("completeness_std_dev", 0)
        confidence_interval = {
            "lower": max(0, recommended["avg_completeness"] - (1.96 * std_dev)),
            "upper": min(100, recommended["avg_completeness"] + (1.96 * std_dev))
        }

        # Monthly cost projection
        monthly_cost = recommended["avg_cost_per_enrichment"] * expected_volume_per_month

        # Alternative strategies
        alternatives = [
            {
                "variant_key": c["variant_key"],
                "variant_name": c["variant_name"],
                "cost": c["avg_cost_per_enrichment"],
                "completeness": c["avg_completeness"],
                "confidence": c["avg_confidence"],
                "roi": c["roi"],
                "note": self._generate_alternative_note(c, recommended)
            }
            for c in candidates[:3]  # Top 3
            if c["variant_key"] != recommended["variant_key"]
        ]

        # Save recommendation to history
        await self.repo.create_recommendation(
            budget_per_enrichment=budget_per_enrichment,
            min_confidence=min_confidence,
            min_completeness=min_completeness,
            recommended_variant_id=recommended["variant_id"],
            recommended_sources=recommended["sources_config"],
            predicted_cost=recommended["avg_cost_per_enrichment"],
            predicted_completeness=recommended["avg_completeness"],
            predicted_confidence=recommended["avg_confidence"],
            prediction_confidence_interval=confidence_interval,
            recommendation_algorithm="pareto_optimization",
            recommendation_rationale=rationale
        )

        return RecommendationStrategy(
            variant_key=recommended["variant_key"],
            variant_name=recommended["variant_name"],
            sources=recommended["sources_config"],
            predicted_cost=recommended["avg_cost_per_enrichment"],
            predicted_completeness=recommended["avg_completeness"],
            predicted_confidence=recommended["avg_confidence"],
            confidence_interval=confidence_interval,
            rationale=rationale,
            monthly_cost_projection=monthly_cost,
            alternative_strategies=alternatives
        )

    def _generate_rationale(
        self,
        variant: Dict,
        budget: float,
        min_confidence: float,
        min_completeness: float
    ) -> str:
        """Generate human-readable rationale"""
        cost = variant["avg_cost_per_enrichment"]
        completeness = variant["avg_completeness"]
        sample_size = variant["sample_size"]

        if cost <= budget:
            cost_note = f"within budget (${budget:.2f})"
        else:
            cost_note = f"exceeds budget by ${cost - budget:.2f}"

        return (
            f"{variant['variant_name']} achieves {completeness:.1f}% completeness "
            f"at ${cost:.2f} per enrichment ({cost_note}). "
            f"Based on {sample_size} historical enrichments with 95% confidence. "
            f"Best quality-per-dollar ratio: {variant['roi']:.0f}."
        )

    def _generate_alternative_note(self, alt: Dict, recommended: Dict) -> str:
        """Generate note for alternative strategy"""
        if alt["avg_cost_per_enrichment"] > recommended["avg_cost_per_enrichment"]:
            cost_diff = alt["avg_cost_per_enrichment"] - recommended["avg_cost_per_enrichment"]
            quality_diff = alt["avg_completeness"] - recommended["avg_completeness"]
            return f"Higher quality (+{quality_diff:.1f}%) but costs ${cost_diff:.2f} more"
        else:
            cost_diff = recommended["avg_cost_per_enrichment"] - alt["avg_cost_per_enrichment"]
            quality_diff = recommended["avg_completeness"] - alt["avg_completeness"]
            return f"Lower cost (-${cost_diff:.2f}) but {quality_diff:.1f}% less complete"

    def _fallback_recommendation(self) -> RecommendationStrategy:
        """Fallback when no data available"""
        return RecommendationStrategy(
            variant_key="free_only",
            variant_name="Free Only (Zero Cost)",
            sources=["metadata", "ip_api"],
            predicted_cost=0.00,
            predicted_completeness=45.0,
            predicted_confidence=65.0,
            confidence_interval={"lower": 40.0, "upper": 50.0},
            rationale="No historical data available. Starting with free-only strategy.",
            monthly_cost_projection=0.00,
            alternative_strategies=[]
        )
```

**Deliverables**:
- `EnrichmentRecommender` class with Pareto optimization
- Rationale generation
- Confidence interval calculation
- Unit tests for recommendation algorithm

---

#### Day 14-15: Admin API Endpoints
**Tasks**:
- [ ] Create `app/routes/ab_testing_admin.py`

```python
"""
Admin endpoints for A/B testing and recommendations
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from app.core.auth import get_current_admin_user
from app.services.ab_testing.recommender import EnrichmentRecommender
from app.repositories.ab_test_repository import ABTestRepository

router = APIRouter(prefix="/api/admin/ab-tests", tags=["A/B Testing Admin"])

# Request/Response models
class RecommendationRequest(BaseModel):
    budget_per_enrichment: float
    min_confidence: float = 70.0
    min_completeness: float = 60.0
    expected_volume_per_month: int = 1000

@router.get("/dashboard")
async def get_ab_test_dashboard(
    admin_user = Depends(get_current_admin_user)
):
    """Get A/B test dashboard overview"""
    repo = ABTestRepository()
    variants = await repo.get_variant_performance()

    return {
        "success": True,
        "data": {
            "active_variants": variants,
            "total_enrichments": sum(v.get("sample_size", 0) for v in variants)
        }
    }

@router.post("/recommendations/generate")
async def generate_recommendation(
    request: RecommendationRequest,
    admin_user = Depends(get_current_admin_user)
):
    """Generate strategy recommendation"""
    recommender = EnrichmentRecommender()

    recommendation = await recommender.recommend_strategy(
        budget_per_enrichment=request.budget_per_enrichment,
        min_confidence=request.min_confidence,
        min_completeness=request.min_completeness,
        expected_volume_per_month=request.expected_volume_per_month
    )

    return {
        "success": True,
        "recommendation": recommendation.dict()
    }

@router.get("/recommendations/history")
async def get_recommendations_history(
    limit: int = 20,
    admin_user = Depends(get_current_admin_user)
):
    """Get recommendation history"""
    repo = ABTestRepository()
    history = await repo.get_recommendations_history(limit=limit)

    return {
        "success": True,
        "recommendations": history
    }
```

**Deliverables**:
- Admin API routes for A/B testing
- Request/response models
- Authentication integration
- API documentation

---

### Week 4: Testing & Deployment

#### Day 16-18: Testing
**Tasks**:
- [ ] Unit tests (target: 80% coverage)
  - Variant assignment consistency
  - Source filtering
  - Metrics calculation
  - Recommendation algorithm
- [ ] Integration tests
  - Full enrichment flow with A/B testing
  - Metrics collection during enrichment
  - Recommendation generation with real data
- [ ] Load tests
  - Simulate 1,000 enrichments across 3 variants
  - Verify metrics accuracy
  - Dashboard query performance

**Deliverables**:
- Test suite with 50+ tests
- Coverage report (>80%)
- Performance benchmarks

---

#### Day 19-20: Deployment & Documentation
**Tasks**:
- [ ] Run migration in production Supabase
- [ ] Deploy code to production
- [ ] Create admin user guide for A/B testing
- [ ] Create API documentation updates
- [ ] Set up metrics aggregation cron job (every 6 hours)
- [ ] Monitor first 100 enrichments

**Deliverables**:
- Production deployment complete
- Documentation published
- Monitoring dashboard configured
- First A/B test results

---

## Success Criteria

### Technical
- ✅ All database tables, views, functions created successfully
- ✅ Variant assignment is consistent (same session → same variant)
- ✅ Source filtering works correctly
- ✅ Metrics aggregation runs successfully
- ✅ Recommendation algorithm produces valid results
- ✅ All tests pass with >80% coverage

### Business
- ✅ Minimum 100 enrichments per variant collected
- ✅ Dashboard shows real-time variant comparison
- ✅ Recommendation generation completes in <1 second
- ✅ Prediction accuracy within ±5% of actual performance
- ✅ Clear winner identified after 30 days

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Low sample size | Wait for 100+ enrichments before declaring winner |
| Source API changes | Track source-level metrics separately |
| Seasonal variations | Run test for minimum 30 days |
| User behavior changes | Monitor edit rate and completion rate daily |

---

## Next Steps After Phase 7

1. **Phase 8**: Multi-armed bandit for dynamic traffic allocation
2. **Phase 9**: Personalized recommendations per industry
3. **Phase 10**: Auto-optimization (switch to winner automatically)

---

**Plan Version**: 1.0.0
**Created**: 2025-01-09
**Estimated Duration**: 4 weeks
**Team Size**: 1-2 developers
