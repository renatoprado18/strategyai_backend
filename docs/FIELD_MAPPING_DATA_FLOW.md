# Progressive Enrichment Data Flow - Field Mapping Analysis

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│ LAYER 1: Metadata + IP API (<2s)                                    │
└─────────────────────────────────────────────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────────────┐
│ metadata.py extracts:                                                 │
│ {                                                                     │
│   "company_name": "TechStart",      ← NOT "name"                     │
│   "description": "B2B SaaS...",                                      │
│   "meta_description": "...",                                         │
│   "website_tech": ["React"],                                         │
│   "logo_url": "https://..."                                          │
│ }                                                                     │
└──────────────────────────────────────────────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────────────┐
│ progressive_orchestrator._update_auto_fill_suggestions()             │
│                                                                       │
│ for field, value in new_data.items():                                │
│     session.fields_auto_filled[field] = value                        │
│                                          ↑                            │
│                                          └─ PROBLEM: Uses raw field   │
│                                             name "company_name"       │
└──────────────────────────────────────────────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────────────┐
│ session.fields_auto_filled = {                                       │
│   "company_name": "TechStart",      ← Frontend needs "name"          │
│   "description": "B2B SaaS...",                                      │
│   "meta_description": "...",                                         │
│   "website_tech": ["React"],                                         │
│   "logo_url": "https://..."                                          │
│ }                                                                     │
└──────────────────────────────────────────────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────────────┐
│ SSE Stream Event (enrichment_progressive.py:244-250)                 │
│                                                                       │
│ layer1_data = {                                                      │
│   "status": "layer1_complete",                                       │
│   "fields": session.fields_auto_filled,  ← SENDS RAW NAMES           │
│   "confidence_scores": {...}                                         │
│ }                                                                     │
│ yield f"event: layer1_complete\ndata: {json.dumps(layer1_data)}\n\n" │
└──────────────────────────────────────────────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────────────┐
│ SSE Event Data (sent to frontend):                                   │
│ {                                                                     │
│   "status": "layer1_complete",                                       │
│   "fields": {                                                         │
│     "company_name": "TechStart",    ← Form expects "name"            │
│     "description": "B2B SaaS...",                                    │
│     "website_tech": ["React"]                                        │
│   }                                                                   │
│ }                                                                     │
└──────────────────────────────────────────────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────────────┐
│ Frontend EventSource Handler                                         │
│                                                                       │
│ eventSource.addEventListener('layer1_complete', (e) => {             │
│   const data = JSON.parse(e.data);                                   │
│   autoFillForm(data.fields);  ← Tries to fill "company_name" field  │
│ });                                  but form has "name" field!      │
│                                                                       │
│ RESULT: Field not auto-filled because name mismatch                  │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Layer 2 Field Name Issues

```
┌─────────────────────────────────────────────────────────────────────┐
│ LAYER 2: Clearbit + ReceitaWS + Google Places (3-6s)                │
└─────────────────────────────────────────────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────────────┐
│ clearbit.py extracts:                                                 │
│ {                                                                     │
│   "company_name": "TechStart",      ← Duplicate from Layer 1         │
│   "city": "São Paulo",              ← CORRECT field name             │
│   "state": "SP",                                                     │
│   "country": "BR",                                                   │
│   "employee_count": "25-50"                                          │
│ }                                                                     │
└──────────────────────────────────────────────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────────────┐
│ google_places.py extracts:                                            │
│ {                                                                     │
│   "business_name": "TechStart",     ← THIRD variation!               │
│   "address": "Av. Paulista, 1000", ← Might override "city"          │
│   "phone": "+55 11 1234-5678",                                       │
│   "rating": 4.7                                                      │
│ }                                                                     │
└──────────────────────────────────────────────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────────────┐
│ session.fields_auto_filled (merged from all sources):                │
│ {                                                                     │
│   "company_name": "TechStart",      ← From metadata/clearbit         │
│   "business_name": "TechStart",     ← From google_places             │
│   "city": "São Paulo",              ← From clearbit                  │
│   "address": "Av. Paulista, 1000",  ← From google_places             │
│   "description": "...",                                              │
│   "phone": "+55 11 1234-5678",                                       │
│   "rating": 4.7                                                      │
│ }                                                                     │
│                                                                       │
│ PROBLEM: Two fields for company name, neither called "name"          │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Field Name Conflicts by Source

### Company Name Field (3 variations)

| Source | Field Name | Value |
|--------|-----------|-------|
| Metadata | `company_name` | "TechStart" |
| Clearbit | `company_name` | "TechStart" |
| Google Places | `business_name` | "TechStart" |
| **Frontend Expects** | **`name`** | **"TechStart"** |

**Result:** User must manually enter "name" because none of these match

### Location Fields (Multiple variations)

| Source | Field Name | Value |
|--------|-----------|-------|
| Clearbit | `city` | "São Paulo" |
| Clearbit | `state` | "SP" |
| Clearbit | `location` | "São Paulo, SP, BR" |
| Google Places | `address` | "Av. Paulista, 1000..." |
| **Frontend Expects** | **`city`** | **"São Paulo"** |

**Result:** `city` field exists but might be overridden or not mapped correctly

---

## Current vs. Expected Data Flow

### Current (BROKEN)
```
Backend Fields      SSE Stream          Frontend Form
─────────────      ─────────────       ──────────────
company_name   →   company_name    ✗   name (missing)
business_name  →   business_name   ✗   name (missing)
city           →   city            ?   city (maybe)
address        →   address         ✓   address (works)
```

### Expected (FIXED)
```
Backend Fields      Normalization       SSE Stream       Frontend Form
─────────────      ──────────────      ───────────      ──────────────
company_name   →   name             →  name          →  name ✓
business_name  →   name             →  name          →  name ✓
city           →   city             →  city          →  city ✓
address        →   address          →  address       →  address ✓
```

---

## Fix Implementation Locations

### 1. Add Field Mapping Config
**File:** `app/services/enrichment/progressive_orchestrator.py`
**Line:** After imports (around line 40)

```python
# Field name normalization mapping
# Maps backend source field names to frontend form field names
FIELD_NAME_MAPPING = {
    # Company name variations → "name"
    "company_name": "name",
    "business_name": "name",
    "legal_name": "legal_name",  # Keep separate

    # Location fields
    "city": "city",
    "state": "state",
    "country": "country",
    "address": "address",
    "location": "location",  # Formatted location string

    # Contact fields
    "phone": "phone",
    "website": "website",

    # Business details
    "description": "description",
    "industry": "industry",
    "employee_count": "employee_count",
    "founded_year": "founded_year",

    # Social/web
    "logo_url": "logo_url",
    "rating": "rating",
    "reviews_count": "reviews_count",

    # Keep all other fields as-is
}
```

### 2. Normalize Field Names Before Storing
**File:** `app/services/enrichment/progressive_orchestrator.py`
**Function:** `_update_auto_fill_suggestions()`
**Line:** 435 (current implementation)

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
    NOW WITH FIELD NAME NORMALIZATION
    """
    for field, value in new_data.items():
        if value is not None and value != "":
            # ✅ NORMALIZE FIELD NAME HERE
            frontend_field = FIELD_NAME_MAPPING.get(field, field)

            # Handle conflicts (e.g., company_name vs business_name → both map to "name")
            # Only override if new value has higher confidence
            existing_confidence = session.confidence_scores.get(frontend_field, 0)

            # Calculate confidence with learning system
            confidence = await self._estimate_field_confidence(
                field,
                value,
                source=source_name
            )

            # Only auto-fill if confidence meets threshold AND
            # either field doesn't exist OR new confidence is higher
            if confidence >= confidence_threshold and confidence >= existing_confidence:
                session.fields_auto_filled[frontend_field] = value  # ✅ Use normalized name
                session.confidence_scores[frontend_field] = confidence

                # Store suggestion in database for tracking
                await self._store_auto_fill_suggestion(
                    session_id=session.session_id,
                    field_name=frontend_field,  # ✅ Store normalized name
                    suggested_value=value,
                    source=source_name,
                    confidence_score=confidence / 100.0
                )

                logger.debug(
                    f"Auto-fill: {field} → {frontend_field} = {value} "
                    f"(confidence: {confidence:.1f}%, source: {source_name})"
                )
```

### 3. Document in API Response
**File:** `app/routes/enrichment_progressive.py`
**Update:** Add field mapping to API documentation

---

## Verification Commands

### Test SSE Stream on Railway

```bash
# Connect to Railway SSE stream and check field names
curl -N "https://your-railway-app.railway.app/api/enrichment/progressive/stream/{session_id}"

# Expected output BEFORE fix:
event: layer1_complete
data: {"status":"layer1_complete","fields":{"company_name":"TechStart",...}

# Expected output AFTER fix:
event: layer1_complete
data: {"status":"layer1_complete","fields":{"name":"TechStart",...}
                                             ↑ Should be "name" not "company_name"
```

### Check Railway Logs

```bash
# Before fix:
Layer 1 complete: 11 fields extracted
Fields: company_name, description, website_tech, ...
        ↑ Wrong field name

# After fix:
Layer 1 complete: 11 fields extracted
Fields: name, description, website_tech, ...
        ↑ Correct field name
```

---

## Priority Fields to Fix

1. **HIGH PRIORITY** (blocking user input)
   - `company_name` / `business_name` → `name`
   - `city` → `city` (verify mapping)

2. **MEDIUM PRIORITY** (nice to have)
   - `phone` → `phone`
   - `address` → `address`
   - `description` → `description`

3. **LOW PRIORITY** (enhancement fields)
   - `rating` → `rating`
   - `employee_count` → `employee_count`
   - `founded_year` → `founded_year`

---

## Conclusion

The field mapping issue is caused by:
1. Backend sources using different field names (`company_name`, `business_name`)
2. No normalization layer to translate to frontend field names
3. SSE stream sending raw backend field names

**Fix:** Implement field name normalization in `_update_auto_fill_suggestions()` as shown above.
