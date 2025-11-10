# Progressive Enrichment Field Mapping Issue - Root Cause Analysis

**Date:** 2025-01-10
**Status:** CRITICAL - Fields extracted but not auto-filling in frontend
**Impact:** User manually filled "name" and "city" despite 16 fields being extracted

---

## Executive Summary

The progressive enrichment system is **extracting 16 fields successfully** (confirmed in Railway logs), but these fields are **NOT auto-filling in the frontend form** because of **field name mismatches** between backend extraction and frontend expectations.

### The Problem

**Backend extracts:**
- `company_name` (from metadata/clearbit)
- `city` (from clearbit)
- `business_name` (from google places)

**Frontend form expects:**
- `name` (NOT `company_name`)
- `city` (exists but might not be mapped)
- Unknown exact field mapping

---

## Detailed Analysis

### 1. Backend Field Extraction (Lines 244-272 in enrichment_progressive.py)

The SSE stream sends `session.fields_auto_filled` directly to the frontend:

```python
# Layer 1 Complete Event
layer1_data = {
    "status": "layer1_complete",
    "fields": session.fields_auto_filled,  # ← SENDS EXACT FIELD NAMES
    "confidence_scores": session.confidence_scores,
    "layer_result": session.layer1_result.dict() if session.layer1_result else {}
}
yield f"event: layer1_complete\ndata: {json.dumps(layer1_data)}\n\n"
```

**Critical Issue:** The `fields` object contains the **exact field names from the data sources**, NOT the field names the frontend form expects.

### 2. Field Names Extracted by Each Source

#### Metadata Source (Layer 1)
**File:** `app/services/enrichment/sources/metadata.py` (line 158)

```python
data = {
    "company_name": self._extract_company_name(soup, domain),  # ← NOT "name"
    "description": self._extract_description(soup),
    "meta_description": self._extract_meta_description(soup),
    "meta_keywords": self._extract_meta_keywords(soup),
    "website_tech": self._detect_technologies(html_content, response.headers),
    "logo_url": self._extract_logo(soup, url),
    "social_media": self._extract_social_media(soup),
}
```

**Fields extracted:** `company_name`, `description`, `meta_description`, `meta_keywords`, `website_tech`, `logo_url`, `social_media`

#### Clearbit Source (Layer 2)
**File:** `app/services/enrichment/sources/clearbit.py` (lines 139-202)

```python
# Basic info
if data.get("name"):
    enriched_data["company_name"] = data["name"]  # ← NOT "name"

if data.get("legalName"):
    enriched_data["legal_name"] = data["legalName"]

# Location
if data.get("location"):
    # ...
    if data["location"].get("city"):
        enriched_data["city"] = data["location"]["city"]  # ← CORRECT

    if data["location"].get("state"):
        enriched_data["state"] = data["location"]["state"]

    if data["location"].get("country"):
        enriched_data["country"] = data["location"]["country"]
```

**Fields extracted:** `company_name`, `legal_name`, `city`, `state`, `country`, `employee_count`, `annual_revenue`, `founded_year`, etc.

#### Google Places Source (Layer 2)
**File:** `app/services/enrichment/sources/google_places.py` (lines 256-257)

```python
if result.get("name"):
    enriched_data["business_name"] = result["name"]  # ← THIRD VARIATION!

if result.get("formatted_address"):
    enriched_data["address"] = result["formatted_address"]
```

**Fields extracted:** `business_name`, `address`, `phone`, `rating`, `reviews_count`, `place_id`, etc.

### 3. The Field Name Mismatch

**Backend has THREE different variations for company name:**
1. `company_name` (Metadata, Clearbit)
2. `business_name` (Google Places)
3. NONE called just `name` (which frontend likely expects)

**Backend has multiple location fields:**
1. `city` (Clearbit) ✓ Correct
2. `address` (Google Places)
3. `location` (formatted string like "São Paulo, SP")

---

## Railway Logs Evidence

User reported Railway logs showed:
- **Layer 1:** 11 fields extracted
- **Layer 3:** 5 fields extracted
- **Total:** 16 fields in `session.fields_auto_filled`

But user had to manually fill:
- `name` ← Backend sent `company_name` instead
- `city` ← Might be sent but form field name doesn't match

---

## SSE Stream Analysis

### What the SSE Stream Actually Sends

```json
{
  "status": "layer1_complete",
  "fields": {
    "company_name": "TechStart Innovations",  // ← Frontend expects "name"
    "description": "B2B SaaS platform...",
    "meta_description": "...",
    "website_tech": ["React", "Next.js"],
    "logo_url": "https://...",
    "social_media": {...}
  },
  "confidence_scores": {
    "company_name": 70.0,
    "description": 70.0,
    ...
  }
}
```

### What the Frontend Form Expects

Based on standard form conventions and the user's reported manual input:
```json
{
  "name": "TechStart Innovations",     // ← NOT "company_name"
  "city": "São Paulo",                 // ← Might match, depends on form
  "description": "...",                // ← Probably matches
  "website": "...",                    // ← Probably matches
  ...
}
```

---

## Root Cause Summary

### Primary Issue: Field Name Translation Missing

The backend SSE stream sends raw field names from data sources (`company_name`, `business_name`) without translating them to the field names the frontend form expects (`name`).

### Why It Happens

1. **No mapping layer:** `progressive_orchestrator.py` stores fields with source field names
2. **Direct passthrough:** `enrichment_progressive.py` sends `session.fields_auto_filled` directly
3. **Frontend expects different names:** Form likely uses `name` not `company_name`

### The Fix Required

**Option 1: Backend Field Name Normalization (RECOMMENDED)**

Add a field mapping layer in `progressive_orchestrator.py` to normalize field names:

```python
FIELD_NAME_MAPPING = {
    # Source field -> Frontend field
    "company_name": "name",
    "business_name": "name",
    "legal_name": "legal_name",  # Keep as-is
    "city": "city",  # Keep as-is
    "address": "address",  # Keep as-is
    # Add more mappings...
}

async def _update_auto_fill_suggestions(self, session, new_data, source_name, confidence_threshold):
    for field, value in new_data.items():
        # Normalize field name
        frontend_field = FIELD_NAME_MAPPING.get(field, field)

        if confidence >= confidence_threshold:
            session.fields_auto_filled[frontend_field] = value  # ← Use normalized name
            session.confidence_scores[frontend_field] = confidence
```

**Option 2: Frontend Field Name Mapping**

Add mapping on the frontend when processing SSE events:

```typescript
const BACKEND_TO_FRONTEND_FIELDS = {
  'company_name': 'name',
  'business_name': 'name',
  'city': 'city',
  // ...
};

eventSource.addEventListener('layer1_complete', (e) => {
  const data = JSON.parse(e.data);

  // Map backend fields to frontend fields
  const mappedFields = {};
  for (const [backendField, value] of Object.entries(data.fields)) {
    const frontendField = BACKEND_TO_FRONTEND_FIELDS[backendField] || backendField;
    mappedFields[frontendField] = value;
  }

  // Now auto-fill with mapped fields
  autoFillForm(mappedFields);
});
```

---

## Recommended Solution

### Implement Backend Field Normalization (Preferred)

**Why backend normalization is better:**
1. Single source of truth
2. API contract consistency
3. Multiple frontends can use same API
4. Easier to maintain field mapping in one place
5. Better for API documentation

### Implementation Steps

1. **Create field mapping config** in `app/services/enrichment/progressive_orchestrator.py`
2. **Normalize in `_update_auto_fill_suggestions()`** before storing in session
3. **Update confidence scores** to use normalized names
4. **Document the mapping** in API docs
5. **Add tests** to verify field name normalization

---

## Testing Verification

### To verify the fix works:

1. **Start progressive enrichment** for a website
2. **Monitor SSE stream** and check field names in events
3. **Verify frontend form** auto-fills with correct values
4. **Check Railway logs** to confirm field mapping

### Expected Railway logs after fix:

```
Layer 1 complete: 11 fields extracted
Fields: name, description, logo_url, website_tech, ...
↑ Should show "name" not "company_name"

Layer 2 complete: 5 additional fields
Fields: city, address, phone, rating, reviews_count
↑ Should match frontend form field names
```

---

## Impact Assessment

**Current State:**
- ❌ 16 fields extracted but NOT auto-filling
- ❌ User must manually enter "name" and "city"
- ❌ Poor user experience despite working enrichment

**After Fix:**
- ✅ 16 fields extracted AND auto-filled
- ✅ User only needs to verify/edit pre-filled values
- ✅ "Wow moment" as form populates instantly

---

## Next Steps

1. **Confirm frontend field names** by reviewing the actual form code
2. **Implement backend field normalization** with mapping config
3. **Test on Railway** with real SSE stream
4. **Update API documentation** with field mapping table
5. **Add monitoring** to track auto-fill success rate

---

## Field Mapping Reference Table

| Source | Backend Field | Frontend Field | Priority |
|--------|--------------|----------------|----------|
| Metadata | `company_name` | `name` | HIGH |
| Clearbit | `company_name` | `name` | HIGH |
| Google Places | `business_name` | `name` | HIGH |
| Clearbit | `city` | `city` | HIGH |
| Clearbit | `state` | `state` | MEDIUM |
| Clearbit | `country` | `country` | MEDIUM |
| Google Places | `address` | `address` | HIGH |
| Google Places | `phone` | `phone` | HIGH |
| Metadata | `description` | `description` | MEDIUM |
| Clearbit | `employee_count` | `employee_count` | LOW |
| Google Places | `rating` | `rating` | LOW |

**Note:** This table needs to be confirmed against the actual frontend form field names.

---

## Conclusion

The progressive enrichment system is **working correctly on the backend** (extracting 16 fields), but the **field name mismatch** prevents the frontend from auto-filling the form. The fix requires implementing a field name normalization layer to translate backend field names (`company_name`, `business_name`) to frontend field names (`name`).

**Recommended Action:** Implement backend field normalization as described in Option 1 above.
