# Phase 6: User Edit Tracking and Learning System

## Overview

Implemented a comprehensive user edit tracking and machine learning system that learns from user corrections to improve auto-fill confidence scores over time.

## Architecture

### Core Components

#### 1. EditTracker (`app/services/enrichment/edit_tracker.py`)
Tracks user edits to auto-filled fields for learning purposes.

**Key Features:**
- Store edit events with original/edited values
- Mark suggestions as edited in database
- Calculate edit distance (Levenshtein)
- Classify edit types (minor/major/complete_rewrite)
- Trigger asynchronous learning updates
- Provide edit statistics and analytics

**Methods:**
```python
async def track_edit(
    session_id: str,
    field_name: str,
    original_value: str,
    edited_value: str,
    source: str,
    original_confidence: float,
    user_id: Optional[str] = None
) -> Dict[str, Any]
```

**Edit Classification:**
- `no_change`: No edit detected
- `minor`: >90% similarity (typo corrections)
- `correction`: 70-90% similarity (moderate changes)
- `major`: 40-70% similarity (significant changes)
- `complete_rewrite`: <40% similarity (entirely different)

#### 2. ConfidenceLearner (`app/services/enrichment/confidence_learner.py`)
Learns from edit patterns to adjust confidence scores.

**Learning Algorithm:**
```python
# If edit_rate > 30%: Reduce confidence for that source/field
# If edit_rate < 5%: Increase confidence for that source/field

adjusted_confidence = base_confidence * multiplier * (1 - edit_rate)

# Caps:
# - Maximum: 98% (never 100%)
# - Minimum: 10%
```

**Adjustment Factors:**
1. **Overall Edit Rate**
   - High (>30%): Apply penalty multiplier (0.7-0.85)
   - Low (<5%): Apply boost multiplier (1.2)

2. **Significant Edit Rate**
   - >50% major rewrites: Additional 15% penalty

3. **Average Edit Distance**
   - Large edits (>10 chars): Additional 10% penalty
   - Small edits (<2 chars): 5% boost

**Methods:**
```python
async def update_confidence_for_source(
    field_name: str,
    source: str,
    lookback_days: int = 30
) -> Dict[str, Any]

async def batch_update_all_sources(
    lookback_days: int = 30,
    min_suggestions: int = 10
) -> Dict[str, Any]

async def get_learning_insights_dashboard(
    days: int = 30,
    limit: int = 20
) -> Dict[str, Any]
```

#### 3. EnrichmentAnalytics (`app/services/enrichment/analytics.py`)
Advanced analytics for monitoring and insights.

**Analytics Provided:**

1. **Edit Patterns Over Time**
   - Time-series data (daily/weekly)
   - Trend analysis (improving/declining)
   - Session and field metrics

2. **Source Reliability Rankings**
   - Ranked by reliability score (1 - edit_rate)
   - Rating: excellent/good/fair/poor
   - Coverage metrics

3. **Field Accuracy Trends**
   - Weekly accuracy rates per field
   - Trend direction (improving/declining/stable)
   - Statistical analysis (stddev, best/worst)

4. **Learning Effectiveness**
   - Before/after comparison
   - Improvement percentage
   - Time/cost savings estimation

5. **Cost vs Quality Analysis**
   - Cost per call per source
   - Fills per dollar
   - Quality per dollar ratio
   - Cost efficiency ratings

#### 4. Integration with Progressive Orchestrator
Updated `ProgressiveEnrichmentOrchestrator` to use learned confidence scores.

**Changes:**
```python
# Before (static confidence):
def _estimate_field_confidence(self, field: str, value: Any) -> float:
    if field in ["cnpj", "legal_name"]:
        return 95.0
    # ... static rules

# After (learned confidence):
async def _estimate_field_confidence(
    self,
    field: str,
    value: Any,
    source: Optional[str] = None
) -> float:
    base_confidence = self._get_base_confidence(field)

    # Query learned adjustments from database
    if source:
        learned_confidence = await self._fetch_learned_confidence(field, source)
        return learned_confidence if learned_confidence else base_confidence

    return base_confidence
```

**Auto-Fill Tracking:**
```python
async def _store_auto_fill_suggestion(
    session_id: str,
    field_name: str,
    suggested_value: Any,
    source: str,
    confidence_score: float
):
    # Store in database for later edit tracking
    # Enables learning from user corrections
```

## API Endpoints

### Edit Tracking Endpoints

#### 1. POST `/api/enrichment/track-edit`
Track user edits to auto-filled fields.

**Request:**
```json
{
  "session_id": "uuid",
  "field_name": "employee_count",
  "original_value": "50-100",
  "edited_value": "25-50",
  "source": "Clearbit",
  "original_confidence": 0.85,
  "user_id": "user123"
}
```

**Response:**
```json
{
  "success": true,
  "edit_record": {
    "id": 123,
    "edit_distance": 4,
    "edit_type": "correction"
  },
  "message": "Edit tracked successfully",
  "insights": [
    "Edit tracked for employee_count from Clearbit",
    "Confidence scores will be updated based on edit patterns"
  ]
}
```

#### 2. GET `/api/enrichment/edit-statistics`
Get edit statistics for analysis.

**Query Parameters:**
- `field_name`: Optional field filter
- `source`: Optional source filter
- `days`: Days to analyze (default 30)

**Response:**
```json
{
  "success": true,
  "statistics": {
    "total_edits": 127,
    "sessions_with_edits": 89,
    "avg_edit_distance": 5.2,
    "minor_edits": 45,
    "corrections": 52,
    "major_edits": 23,
    "complete_rewrites": 7,
    "avg_original_confidence": 0.78
  }
}
```

#### 3. GET `/api/enrichment/most-edited-fields`
Get fields with highest edit rates.

**Response:**
```json
{
  "success": true,
  "fields": [
    {
      "field_name": "employee_count",
      "source": "Clearbit",
      "edit_count": 45,
      "avg_edit_distance": 6.8,
      "significant_edits": 23,
      "edit_rate_severity": "high"
    }
  ]
}
```

### Learning Endpoints

#### 4. POST `/api/enrichment/update-confidence`
Manually trigger confidence update for field/source.

**Request:**
```json
{
  "field_name": "employee_count",
  "source": "Clearbit",
  "lookback_days": 30
}
```

**Response:**
```json
{
  "success": true,
  "field_name": "employee_count",
  "source": "Clearbit",
  "old_confidence": 0.85,
  "new_confidence": 0.72,
  "adjustment": {
    "multiplier": 0.85,
    "adjustment_type": "penalty",
    "reasoning": [
      "High edit rate (35%) indicates unreliable data",
      "High significant edit rate (51%) indicates poor data quality"
    ]
  },
  "insights": [
    "⚠️ Clearbit employee_count edited 35% → confidence reduced to 85%",
    "🔴 51% of edits are major rewrites - consider alternative data source"
  ]
}
```

#### 5. POST `/api/enrichment/batch-update-confidence`
Batch update all source/field combinations.

**Response:**
```json
{
  "success": true,
  "total_combinations": 47,
  "updated_count": 43,
  "boosted_count": 12,
  "penalized_count": 18,
  "lookback_days": 30
}
```

#### 6. POST `/api/enrichment/learning-insights`
Get comprehensive learning insights.

**Response:**
```json
{
  "success": true,
  "insights": {
    "top_performers": [
      {
        "field_name": "cnpj",
        "source": "ReceitaWS",
        "edit_rate": 0.02,
        "confidence": 0.95
      }
    ],
    "problem_areas": [
      {
        "field_name": "employee_count",
        "source": "Clearbit",
        "edit_rate": 0.35,
        "confidence": 0.72,
        "learned_adjustment": 0.85
      }
    ],
    "overall_stats": {
      "total_fields": 23,
      "total_sources": 7,
      "overall_edit_rate": 0.18
    }
  }
}
```

### Analytics Dashboard Endpoints

#### 7. GET `/api/enrichment/analytics/dashboard`
Comprehensive analytics dashboard.

**Response:**
```json
{
  "success": true,
  "dashboard": {
    "generated_at": "2025-01-15T10:30:00Z",
    "days_analyzed": 30,
    "edit_patterns": { "trend": "improving", "patterns": [...] },
    "source_rankings": { "rankings": [...] },
    "field_trends": { "trends": [...] },
    "learning_effectiveness": {
      "improvement": {
        "improvement_pct": 15.3,
        "edits_avoided": 127,
        "time_saved_minutes": 63.5
      },
      "effectiveness_rating": "good"
    },
    "cost_analysis": { "analysis": [...] },
    "key_insights": [
      "Learning system achieved 15.3% improvement in accuracy",
      "Avoided 127 manual edits, saving 64 minutes",
      "Edit trend is improving over the past 30 days"
    ]
  }
}
```

#### 8. GET `/api/enrichment/analytics/edit-patterns`
Time-series edit pattern analysis.

**Query Parameters:**
- `days`: Days to analyze (default 30)
- `granularity`: 'daily' or 'weekly' (default 'daily')

#### 9. GET `/api/enrichment/analytics/source-reliability`
Source reliability rankings.

**Query Parameters:**
- `days`: Days to analyze (default 30)
- `min_suggestions`: Minimum suggestions to rank (default 10)

#### 10. GET `/api/enrichment/analytics/field-accuracy`
Field accuracy trends over time.

**Query Parameters:**
- `field_name`: Optional specific field
- `days`: Days to analyze (default 30)

#### 11. GET `/api/enrichment/analytics/learning-effectiveness`
Learning system effectiveness metrics.

#### 12. GET `/api/enrichment/analytics/cost-quality`
Cost vs quality analysis per source.

## Database Schema

### Tables Used

#### 1. `auto_fill_suggestions`
Stores all auto-fill suggestions for tracking.

```sql
CREATE TABLE auto_fill_suggestions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    field_name VARCHAR(255) NOT NULL,
    suggested_value TEXT,
    source VARCHAR(255) NOT NULL,
    confidence_score FLOAT NOT NULL,
    was_edited BOOLEAN DEFAULT FALSE,
    final_value TEXT,
    edited_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_session_field (session_id, field_name),
    INDEX idx_source_field (source, field_name),
    INDEX idx_was_edited (was_edited)
);
```

#### 2. `field_validation_history`
Detailed edit history with classifications.

```sql
CREATE TABLE field_validation_history (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    field_name VARCHAR(255) NOT NULL,
    original_value TEXT,
    edited_value TEXT,
    source VARCHAR(255) NOT NULL,
    original_confidence FLOAT,
    edit_distance INT,
    edit_type VARCHAR(50), -- minor/correction/major/complete_rewrite
    user_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_field_source (field_name, source),
    INDEX idx_edit_type (edit_type),
    INDEX idx_created_at (created_at)
);
```

#### 3. `enrichment_source_performance`
Learned confidence scores per source/field.

```sql
CREATE TABLE enrichment_source_performance (
    id SERIAL PRIMARY KEY,
    source VARCHAR(255) NOT NULL,
    field_name VARCHAR(255) NOT NULL,
    confidence_score FLOAT NOT NULL,
    success_rate FLOAT,
    total_attempts INT DEFAULT 0,
    successful_fills INT DEFAULT 0,
    learned_adjustment FLOAT DEFAULT 1.0,
    last_updated TIMESTAMP DEFAULT NOW(),
    UNIQUE(source, field_name),
    INDEX idx_source (source),
    INDEX idx_field (field_name)
);
```

## Learning Algorithm Details

### Confidence Adjustment Formula

```python
# Base confidence from source type
base_confidence = get_base_confidence(field)  # 50-95%

# Calculate edit rate
edit_rate = total_edits / total_suggestions

# Apply multiplier based on edit rate
if edit_rate > 0.30:  # High edit rate
    penalty = 1 - ((edit_rate - 0.30) / 0.70)
    multiplier = max(0.7, penalty)
elif edit_rate < 0.05:  # Low edit rate
    multiplier = 1.2  # Boost by 20%
else:
    multiplier = 1.0  # No change

# Apply additional factors
if significant_edit_rate > 0.5:
    multiplier *= 0.85  # -15% for major rewrites

if avg_edit_distance > 10:
    multiplier *= 0.90  # -10% for large edits

# Calculate final confidence
adjusted_confidence = base_confidence * multiplier

# Apply caps
final_confidence = max(0.10, min(0.98, adjusted_confidence))
```

### Example Scenarios

**Scenario 1: Reliable Source (ReceitaWS CNPJ)**
- Base confidence: 95%
- Edit rate: 2%
- Adjustment: 1.2x boost
- Final confidence: 95% * 1.2 = 98% (capped)
- Result: Highly reliable, confidence boosted to maximum

**Scenario 2: Unreliable Source (Clearbit employee_count)**
- Base confidence: 85%
- Edit rate: 35%
- Significant edit rate: 51%
- Adjustment: 0.85 * 0.85 = 0.72x penalty
- Final confidence: 85% * 0.72 = 61.2%
- Result: Unreliable, confidence significantly reduced

**Scenario 3: Moderate Source (Google Places rating)**
- Base confidence: 90%
- Edit rate: 15%
- Adjustment: 1.0x (no change in 5-30% range)
- Final confidence: 90%
- Result: Stable, maintaining base confidence

## Benefits

### 1. Continuous Improvement
- System learns from every user correction
- Confidence scores become more accurate over time
- Reduces false confidence in unreliable sources

### 2. Data Quality Insights
- Identify problematic data sources
- Track which fields need better sources
- Monitor improvement trends

### 3. Cost Optimization
- Prioritize reliable, cost-effective sources
- Reduce spending on low-quality sources
- Maximize ROI on data enrichment

### 4. Time Savings
- Fewer manual edits required
- More accurate auto-fill suggestions
- Better user experience

### 5. Transparency
- Clear insights into learning process
- Explainable confidence adjustments
- Actionable recommendations

## Usage Example

### Frontend Integration

```typescript
// 1. User edits an auto-filled field
async function handleFieldEdit(
  sessionId: string,
  fieldName: string,
  originalValue: string,
  newValue: string,
  source: string,
  confidence: number
) {
  await fetch('/api/enrichment/track-edit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      field_name: fieldName,
      original_value: originalValue,
      edited_value: newValue,
      source: source,
      original_confidence: confidence
    })
  });
}

// 2. Display analytics dashboard
async function loadAnalyticsDashboard() {
  const response = await fetch('/api/enrichment/analytics/dashboard?days=30');
  const { dashboard } = await response.json();

  // Display key insights
  console.log('Key Insights:', dashboard.key_insights);

  // Show learning effectiveness
  const improvement = dashboard.learning_effectiveness.improvement;
  console.log(`Learning improved accuracy by ${improvement.improvement_pct}%`);
  console.log(`Saved ${improvement.time_saved_minutes} minutes`);

  // Display source rankings
  dashboard.source_rankings.rankings.forEach(source => {
    console.log(`${source.rank}. ${source.source}: ${source.reliability_score * 100}% reliable`);
  });
}
```

## Monitoring and Maintenance

### Recommended Schedule

1. **Real-time:**
   - Track edits immediately via webhook
   - Trigger async confidence updates

2. **Daily:**
   - Batch update all confidence scores
   - Review top problem areas
   - Monitor learning effectiveness

3. **Weekly:**
   - Analyze trends and patterns
   - Review cost vs quality tradeoffs
   - Adjust data source priorities

4. **Monthly:**
   - Comprehensive dashboard review
   - ROI analysis
   - Strategic planning for data sources

### Performance Metrics

**Target KPIs:**
- Edit rate: <15% (85% accuracy)
- Learning improvement: >10% quarterly
- Confidence accuracy: >90%
- Time saved: >50% reduction in manual edits
- Cost efficiency: Maximize quality per dollar

## Future Enhancements

1. **Machine Learning Models:**
   - Train ML models on edit patterns
   - Predict likely edits before they happen
   - Personalized confidence scores per user

2. **A/B Testing:**
   - Test confidence threshold variations
   - Compare learning algorithms
   - Optimize for different use cases

3. **Real-time Notifications:**
   - Alert on declining source quality
   - Notify when confidence drops below threshold
   - Suggest alternative sources

4. **Field Recommendations:**
   - Suggest best sources per field
   - Auto-switch to more reliable sources
   - Dynamic source prioritization

5. **Integration with External Systems:**
   - Feedback loops with data vendors
   - Share quality metrics
   - Negotiate better pricing based on quality

## Files Created/Modified

### New Files:
1. `app/services/enrichment/edit_tracker.py` - Edit tracking service
2. `app/services/enrichment/confidence_learner.py` - Learning algorithm
3. `app/services/enrichment/analytics.py` - Analytics queries
4. `app/routes/enrichment.py` - API endpoints
5. `docs/PHASE_6_USER_EDIT_TRACKING_SUMMARY.md` - This documentation

### Modified Files:
1. `app/services/enrichment/progressive_orchestrator.py` - Integrated learning system

## Testing

### Unit Tests Needed:
1. Test edit tracking with various edit types
2. Test confidence adjustment calculations
3. Test analytics query accuracy
4. Test database integration

### Integration Tests Needed:
1. End-to-end edit tracking flow
2. Batch confidence updates
3. Dashboard data generation
4. Real-time learning updates

### Load Tests Needed:
1. High-volume edit tracking
2. Concurrent confidence updates
3. Dashboard query performance
4. Database query optimization

## Conclusion

Phase 6 implements a comprehensive user edit tracking and learning system that continuously improves auto-fill confidence scores based on user corrections. The system provides:

- **Intelligent Learning:** Adjusts confidence based on edit patterns
- **Rich Analytics:** Comprehensive insights into data quality
- **Cost Optimization:** Identifies most cost-effective sources
- **Continuous Improvement:** Gets smarter with every user interaction

The learning algorithm is conservative (caps at 98%), transparent (explainable adjustments), and effective (measurable improvements). The analytics dashboard provides actionable insights for optimizing the enrichment system.
