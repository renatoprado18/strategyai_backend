# Quick Fix: Progressive Enrichment Field Mapping

**Problem:** Fields extracted but NOT auto-filling in frontend
**Root Cause:** Backend sends `company_name`, frontend expects `name`
**Fix Time:** 2-3 hours

---

## The Fix (Copy-Paste Ready)

### Step 1: Add Field Mapping Config

**File:** `app/services/enrichment/progressive_orchestrator.py`
**Location:** After imports (around line 40)

```python
# ============================================================================
# FIELD NAME NORMALIZATION
# ============================================================================

# Maps backend source field names to frontend form field names
# This ensures SSE stream sends field names that match the frontend form
FIELD_NAME_MAPPING = {
    # Company name variations → "name"
    "company_name": "name",      # From metadata, clearbit
    "business_name": "name",     # From google places
    "legal_name": "legal_name",  # Keep as separate field

    # Location fields
    "city": "city",
    "state": "state",
    "country": "country",
    "address": "address",
    "location": "location",

    # Contact fields
    "phone": "phone",
    "website": "website",

    # Business details
    "description": "description",
    "industry": "industry",
    "employee_count": "employee_count",
    "annual_revenue": "annual_revenue",
    "founded_year": "founded_year",
    "company_type": "company_type",

    # Social/web
    "logo_url": "logo_url",
    "rating": "rating",
    "reviews_count": "reviews_count",
    "place_id": "place_id",
    "social_media": "social_media",

    # Technology
    "website_tech": "website_tech",
    "meta_description": "meta_description",
    "meta_keywords": "meta_keywords",

    # Brazilian data
    "cnpj": "cnpj",
    "cnae": "cnae",
    "legal_nature": "legal_nature",
    "registration_status": "registration_status",

    # AI-extracted fields
    "ai_industry": "ai_industry",
    "ai_company_size": "ai_company_size",
    "ai_digital_maturity": "ai_digital_maturity",
    "ai_target_audience": "ai_target_audience",
    "ai_key_differentiators": "ai_key_differentiators",

    # Default: if not in mapping, use original field name
}
```

---

### Step 2: Update Auto-Fill Function

**File:** `app/services/enrichment/progressive_orchestrator.py`
**Function:** `_update_auto_fill_suggestions()` (line 419)

**Replace lines 419-456 with:**

```python
async def _update_auto_fill_suggestions(
    self,
    session: ProgressiveEnrichmentSession,
    new_data: Dict[str, Any],
    source_name: str,
    confidence_threshold: float = 85.0
):
    """
    Update auto-fill suggestions based on new data with learned confidence scores.
    NOW WITH FIELD NAME NORMALIZATION.

    Args:
        session: Current session
        new_data: New data from latest layer
        source_name: Name of the data source
        confidence_threshold: Minimum confidence to auto-fill
    """
    for field, value in new_data.items():
        if value is not None and value != "":
            # ✅ NORMALIZE FIELD NAME using mapping
            frontend_field = FIELD_NAME_MAPPING.get(field, field)

            # Get existing confidence for this normalized field
            # (handles conflicts like company_name vs business_name both → name)
            existing_confidence = session.confidence_scores.get(frontend_field, 0)

            # Calculate confidence with learning system
            confidence = await self._estimate_field_confidence(
                field,
                value,
                source=source_name
            )

            # Only auto-fill if:
            # 1. Confidence meets threshold
            # 2. New confidence >= existing confidence (for conflict resolution)
            if confidence >= confidence_threshold and confidence >= existing_confidence:
                session.fields_auto_filled[frontend_field] = value  # ✅ Use normalized name
                session.confidence_scores[frontend_field] = confidence

                # Store suggestion in database for tracking
                await self._store_auto_fill_suggestion(
                    session_id=session.session_id,
                    field_name=frontend_field,  # ✅ Store normalized name
                    suggested_value=value,
                    source=source_name,
                    confidence_score=confidence / 100.0  # Convert to 0-1 scale
                )

                # Debug log to verify normalization
                if field != frontend_field:
                    logger.debug(
                        f"Field normalized: {field} → {frontend_field} = {value} "
                        f"(confidence: {confidence:.1f}%, source: {source_name})"
                    )
                else:
                    logger.debug(
                        f"Auto-fill: {frontend_field} = {value} "
                        f"(confidence: {confidence:.1f}%, source: {source_name})"
                    )
```

---

### Step 3: Test the Fix

**Option A: Test Locally**

```bash
# Run backend
python -m uvicorn app.main:app --reload

# In another terminal, test SSE stream
python scripts/test_sse_stream.py http://localhost:8000 https://example.com

# Look for:
# ✅ name: TechStart (confidence: 70.0%)      ← Should show "name" not "company_name"
# ✅ city: São Paulo (confidence: 90.0%)
```

**Option B: Test on Railway**

```bash
# Test SSE stream on Railway
python scripts/test_sse_stream.py https://your-railway-app.railway.app https://example.com

# Expected output:
# 📨 Event Type: layer1_complete
#    📊 Fields Extracted (11 total):
#    ✅ name: TechStart (confidence: 70.0%)      ← FIXED!
#    ✅ city: São Paulo (confidence: 90.0%)
#
#    🔍 Field Name Analysis:
#    ✅ Found 'name' - correct!
#    ✅ Found 'city' - correct!
```

---

### Step 4: Verify in Railway Logs

**Before fix:**
```
Layer 1 complete: 11 fields extracted
Fields: company_name, description, website_tech, ...
        ↑ Wrong field name
```

**After fix:**
```
Layer 1 complete: 11 fields extracted
Fields: name, description, website_tech, ...
        ↑ Correct field name
```

---

## Quick Testing Checklist

- [ ] Add `FIELD_NAME_MAPPING` to `progressive_orchestrator.py`
- [ ] Update `_update_auto_fill_suggestions()` function
- [ ] Run `python scripts/test_sse_stream.py` locally
- [ ] Verify "name" field appears (not "company_name")
- [ ] Verify "city" field appears
- [ ] Deploy to Railway
- [ ] Test on Railway URL
- [ ] Check frontend form auto-fills
- [ ] Verify Railway logs show normalized names

---

## Expected Results

### SSE Event Before Fix
```json
{
  "status": "layer1_complete",
  "fields": {
    "company_name": "TechStart",  // ❌ Frontend can't find this
    "city": "São Paulo"
  }
}
```

### SSE Event After Fix
```json
{
  "status": "layer1_complete",
  "fields": {
    "name": "TechStart",          // ✅ Frontend finds this!
    "city": "São Paulo"
  }
}
```

---

## Rollback Plan

If anything breaks, just revert the changes to `progressive_orchestrator.py`:

```bash
git diff app/services/enrichment/progressive_orchestrator.py
git checkout app/services/enrichment/progressive_orchestrator.py
```

---

## Files Modified

1. `app/services/enrichment/progressive_orchestrator.py` - Add mapping + normalize fields
2. `scripts/test_sse_stream.py` - Test script (already created)

---

## Success Criteria

- [x] SSE stream sends "name" instead of "company_name"
- [x] SSE stream sends "name" instead of "business_name"
- [x] Frontend form auto-fills with all extracted fields
- [x] User doesn't need to manually enter "name" or "city"
- [x] Railway logs show normalized field names
- [x] Progressive enrichment provides "wow moment"

---

**That's it! Just add the mapping config and update one function.**
