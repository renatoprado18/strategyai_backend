# ADR 003: Confidence Scoring System

## Status

Accepted

## Date

2025-01-09

## Context

Auto-filled form data comes from multiple sources with varying reliability:
- Government registries (95%+ accurate)
- Verified APIs like Clearbit (85%+ accurate)
- AI inference (70-85% accurate)
- IP geolocation (60-70% accurate)

Users need to know:
1. Which fields are reliable (can accept as-is)
2. Which fields need review (may be incorrect)
3. Which source provided each field (for debugging)

Without confidence scores:
- Users don't know which fields to trust
- All auto-filled data appears equal quality
- No guidance on what to review
- Poor user experience (mistrust system)

## Decision

We will implement a **source-based confidence scoring system** with 0-100 scores for each auto-filled field.

### Confidence Calculation

```python
def get_base_confidence(field_name: str, source: str) -> float:
    """
    Calculate confidence score based on field and source.

    Returns: 0-100 score
    """
    # Government-verified data
    if source == "receita_ws":
        return 95.0  # CNPJ, legal name, registration

    # Verified business APIs
    if source == "google_places":
        return 90.0  # Verified address, ratings

    # High-quality business intelligence
    if source == "clearbit":
        return 85.0  # Employee count, revenue estimates

    # AI inference
    if source.startswith("ai_") or source == "openrouter":
        return 75.0  # Industry classification, insights

    # Self-reported metadata
    if source == "metadata":
        return 70.0  # Company name, description

    # Approximate location
    if source == "ip_api":
        return 60.0  # IP-based geolocation

    # Default for unknown sources
    return 50.0
```

### Confidence Tiers

| Tier | Score Range | Visual Indicator | User Action |
|------|-------------|------------------|-------------|
| **High** | 85-100 | Green checkmark | Accept as-is |
| **Medium** | 70-84 | Yellow warning | Review recommended |
| **Low** | 50-69 | Orange caution | Verify before accepting |
| **Very Low** | < 50 | Red alert | Manual entry suggested |

### Field Display

```javascript
// Frontend rendering
function renderField(fieldName, value, confidence) {
  const icon = getConfidenceIcon(confidence);
  const color = getConfidenceColor(confidence);

  return (
    <div className="form-field">
      <input
        value={value}
        onChange={handleEdit}
        style={{ borderColor: color }}
      />
      <span className="confidence-indicator">
        {icon} {confidence}%
      </span>
    </div>
  );
}

function getConfidenceIcon(score) {
  if (score >= 85) return '✓';  // High confidence
  if (score >= 70) return '⚠';  // Medium confidence
  if (score >= 50) return '⚡'; // Low confidence
  return '❌';  // Very low confidence
}
```

## Consequences

### Positive

**Transparency:**
- Users see data reliability
- Know which fields to review
- Understand data provenance
- Build trust in system

**User Experience:**
- Clear visual indicators
- Guided review process
- Reduced data errors
- Confidence in submissions

**Data Quality:**
- Track field accuracy
- Learn from user edits
- Improve scoring over time
- Identify weak sources

**Debugging:**
- Know which source failed
- Track API reliability
- Identify data quality issues
- Monitor improvements

### Negative

**Complexity:**
- More state to manage
- UI complexity increases
- Need to track source for each field
- Storage overhead

**User Confusion:**
- Some users ignore scores
- May distrust low-scored fields unnecessarily
- Overthink simple corrections
- Analysis paralysis

**Calibration Challenges:**
- Hard to validate scores
- User perception vs actual accuracy
- Different industries have different needs
- Scores may need tuning

## Implementation

### Backend Storage

```python
class ProgressiveEnrichmentSession(BaseModel):
    session_id: str
    fields_auto_filled: Dict[str, Any]
    confidence_scores: Dict[str, float]  # field → confidence
    source_attribution: Dict[str, str]   # field → source

# Example:
{
  "fields_auto_filled": {
    "company_name": "TechStart",
    "employee_count": "25-50",
    "industry": "Technology"
  },
  "confidence_scores": {
    "company_name": 70.0,    # Metadata
    "employee_count": 85.0,  # Clearbit
    "industry": 75.0         # AI inference
  },
  "source_attribution": {
    "company_name": "metadata",
    "employee_count": "clearbit",
    "industry": "openrouter"
  }
}
```

### SSE Event Format

```json
{
  "event": "layer2_complete",
  "data": {
    "status": "layer2_complete",
    "fields": {
      "employeeCount": "25-50",
      "industry": "Technology"
    },
    "confidence": {
      "employeeCount": 85.0,
      "industry": 75.0
    },
    "sources": {
      "employeeCount": "clearbit",
      "industry": "openrouter"
    }
  }
}
```

### Frontend Display

```javascript
function FormField({ name, value, confidence, source }) {
  const tier = getConfidenceTier(confidence);

  return (
    <div className={`field confidence-${tier}`}>
      <label>{name}</label>
      <input
        value={value}
        onChange={handleEdit}
        className={`confidence-${tier}-border`}
      />
      <div className="confidence-badge">
        <span className="confidence-icon">{getIcon(tier)}</span>
        <span className="confidence-score">{confidence}%</span>
        <span className="confidence-source">from {source}</span>
      </div>
    </div>
  );
}
```

## Machine Learning Enhancement (Phase 6)

Future improvement: Learn confidence from user edits

```python
class ConfidenceLearner:
    """
    Learn confidence scores from user edit patterns.

    Track:
    - Field edit frequency per source
    - Field acceptance rate per source
    - Time to edit (quick edit = obvious error)
    """

    def learn_from_edit(self, field, source, suggested_value, actual_value):
        """Update confidence based on user edit"""
        if suggested_value == actual_value:
            # User accepted suggestion
            self.boost_confidence(field, source)
        else:
            # User corrected suggestion
            self.reduce_confidence(field, source)

    def get_learned_confidence(self, field, source) -> float:
        """Get confidence adjusted by learning"""
        base_confidence = get_base_confidence(field, source)
        adjustment = self.get_adjustment(field, source)
        return base_confidence + adjustment
```

**Example Learning:**
```python
# After 100 edits:
# Clearbit employee_count: 85.0 → 92.0 (users rarely edit)
# AI industry classification: 75.0 → 68.0 (users often correct)
```

## Alternatives Considered

### Alternative 1: Binary (High/Low)

**Approach:** Simple high/low confidence only

**Pros:**
- Simple implementation
- Clear decision (trust or don't)
- Easy UI

**Cons:**
- Too coarse (loses nuance)
- Can't differentiate 85% vs 95%
- Less useful for users

**Decision:** Rejected - Not enough granularity

### Alternative 2: 5-Star Rating

**Approach:** 1-5 stars like product reviews

**Pros:**
- Familiar to users
- Visual appeal
- Easy to understand

**Cons:**
- Less precise than percentage
- Harder to calculate (discrete values)
- Doesn't map well to probability

**Decision:** Rejected - Percentage more precise

### Alternative 3: No Confidence Scores

**Approach:** Show all data equally, let users decide

**Pros:**
- Simplest implementation
- No complexity
- Users decide everything

**Cons:**
- No guidance for users
- Higher error rate
- Lower trust in system
- More user effort

**Decision:** Rejected - User experience suffers

### Alternative 4: Source Name Only

**Approach:** Just show source (e.g., "from Clearbit")

**Pros:**
- Simple to implement
- Transparent about provenance

**Cons:**
- Users don't know reliability
- Have to learn each source
- No quantitative measure

**Decision:** Rejected - Not user-friendly

## Validation Strategy

Track these metrics:

```python
logger.info(
    "Field suggested",
    extra={
        "field": "employee_count",
        "source": "clearbit",
        "confidence": 85.0,
        "edited_by_user": False  # Track if user edited
    }
)
```

**Key Metrics:**
- Edit rate by confidence tier
  - High (85-100): < 10% edit rate
  - Medium (70-84): 20-30% edit rate
  - Low (50-69): 50-70% edit rate

If edit rates don't match expectations, recalibrate scores.

## Related Decisions

- [ADR 001: 3-Layer Progressive Enrichment](./001-progressive-enrichment.md)
- [ADR 002: SSE Streaming](./002-sse-streaming.md)

## References

- [Nielsen Norman Group: Confidence Ratings](https://www.nngroup.com/articles/confidence-ratings/)
- [Machine Learning Confidence Scores](https://developers.google.com/machine-learning/crash-course/classification/thresholding)

---

*Approved by: Architecture Team*
*Last Updated: January 2025*
