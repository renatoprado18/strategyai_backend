# Field Mapping Analysis - Backend to Frontend

## Problem

User reports that enrichment data is extracted but **not displaying on the form**. Specifically:
- User had to manually enter `name` field (company name)
- User had to manually enter `city` field
- Despite backend logs showing these fields were extracted successfully

## Root Cause

**FIELD NAME MISMATCH** between backend extraction and frontend form expectations.

## Complete Field Mapping

### Layer 1 Fields (Metadata + IP API)

Backend logs show these 11 fields extracted:

| Backend Field Name | Frontend Expects | Source | Notes |
|-------------------|------------------|--------|-------|
| `company_name` | `name` ❌ | Metadata | **MISMATCH - needs translation** |
| `location` | `location` ✅ | IP API (composite) | Already working per user |
| `domain` | `websiteUrl` ✅ | Metadata | Already has data |
| `ip_location` | ??? | IP API | Composite: "City, Region, Country" |
| `city` | `city` ✅ | IP API | Should work if mapped |
| `region` | `state` ❌ | IP API | **MISMATCH** |
| `country` | `country` ✅ | IP API | Country code (e.g., "BR") |
| `country_name` | ??? | IP API | Full name (e.g., "Brazil") |
| `timezone` | `timezone` ✅ | IP API | Should work if mapped |
| `isp` | ??? | IP API | Not used in form |
| `query` (ip_address) | ??? | IP API | Not used in form |

### Layer 2 Fields (Clearbit + ReceitaWS + Google Places)

| Backend Field Name | Frontend Expects | Source | Notes |
|-------------------|------------------|--------|-------|
| `cnpj` | `cnpj` ✅ | ReceitaWS | Brazilian company ID |
| `legal_name` | ??? | ReceitaWS | Official registered name |
| `phone` | `phone` ✅ | Google Places | Should work |
| `rating` | ??? | Google Places | Not used in form |
| `reviews_count` | ??? | Google Places | Not used in form |
| `employee_count` | `employeeCount` ❌ | Clearbit | **MISMATCH** (snake vs camel) |
| `annual_revenue` | `annualRevenue` ❌ | Clearbit | **MISMATCH** (snake vs camel) |

### Layer 3 Fields (AI Inference + Proxycurl)

| Backend Field Name | Frontend Expects | Source | Notes |
|-------------------|------------------|--------|-------|
| `ai_industry` | `industry` ❌ | OpenRouter | **MISMATCH - remove prefix** |
| `ai_company_size` | `companySize` ❌ | OpenRouter | **MISMATCH - remove prefix + camel** |
| `ai_digital_maturity` | `digitalMaturity` ❌ | OpenRouter | **MISMATCH - remove prefix + camel** |
| `ai_target_audience` | `targetAudience` ❌ | OpenRouter | **MISMATCH - remove prefix + camel** |
| `ai_key_differentiators` | `keyDifferentiators` ❌ | OpenRouter | **MISMATCH - remove prefix + camel** |

## Critical Mismatches Preventing Auto-Fill

### HIGH PRIORITY (User manually entered these)

1. **Company Name**
   - Backend: `company_name`
   - Frontend: `name`
   - **Impact**: User had to type company name despite it being extracted

2. **City**
   - Backend: `city` (exists in data)
   - Frontend: `city` (should match, but check if SSE is sending it)
   - **Impact**: User had to type city despite it being extracted

3. **Region/State**
   - Backend: `region` (e.g., "São Paulo")
   - Frontend: `state`
   - **Impact**: State field empty

### MEDIUM PRIORITY (Form fields exist)

4. **AI Fields** - All have `ai_` prefix that frontend doesn't expect:
   - `ai_industry` → `industry`
   - `ai_company_size` → `companySize`
   - `ai_digital_maturity` → `digitalMaturity`
   - `ai_target_audience` → `targetAudience`
   - `ai_key_differentiators` → `keyDifferentiators`

5. **Clearbit Fields** - Snake case vs camel case:
   - `employee_count` → `employeeCount`
   - `annual_revenue` → `annualRevenue`

## Solution: Field Translation Layer

Add translation in `enrichment_progressive.py` SSE stream before sending to frontend:

```python
def translate_fields_for_frontend(backend_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Translate backend field names to frontend form field names.

    This function maps the snake_case backend fields (and ai_ prefixed fields)
    to the camelCase fields expected by the frontend form.
    """
    translation_map = {
        # Layer 1 (Metadata + IP API)
        "company_name": "name",           # CRITICAL FIX
        "region": "state",                 # CRITICAL FIX
        "country_name": "countryName",
        "ip_address": "ipAddress",

        # Layer 2 (Clearbit + ReceitaWS + Google)
        "employee_count": "employeeCount",
        "annual_revenue": "annualRevenue",
        "legal_name": "legalName",

        # Layer 3 (AI Inference - remove ai_ prefix)
        "ai_industry": "industry",
        "ai_company_size": "companySize",
        "ai_digital_maturity": "digitalMaturity",
        "ai_target_audience": "targetAudience",
        "ai_key_differentiators": "keyDifferentiators",
    }

    # Apply translation
    frontend_data = {}
    for backend_key, value in backend_data.items():
        # Use translated name if available, otherwise keep original
        frontend_key = translation_map.get(backend_key, backend_key)
        frontend_data[frontend_key] = value

    return frontend_data
```

## Implementation Steps

1. **Add translation function** to `app/routes/enrichment_progressive.py`
2. **Apply translation** in SSE stream events before sending `fields` to frontend
3. **Apply translation** in session status endpoint
4. **Test with frontend** to verify auto-fill works

## Testing Checklist

After fix, verify these fields auto-fill:

- [ ] `name` (company_name) - User should NOT have to type this
- [ ] `city` - User should NOT have to type this
- [ ] `state` (region) - Should auto-fill
- [ ] `country` - Should auto-fill
- [ ] `industry` (ai_industry) - Should auto-fill after Layer 3
- [ ] `companySize` (ai_company_size) - Should auto-fill after Layer 3
- [ ] `employeeCount` (employee_count) - Should auto-fill after Layer 2

## Expected Behavior After Fix

**Layer 1 Complete (< 2s)**:
```json
{
  "fields": {
    "name": "Google",              // ← Was company_name
    "location": "Sao Paulo, SP",   // ← Already working
    "city": "Sao Paulo",            // ← Should work now
    "state": "SP",                  // ← Was region
    "country": "BR",
    "timezone": "America/Sao_Paulo"
  }
}
```

**Layer 3 Complete (6-10s)**:
```json
{
  "fields": {
    "name": "Google",
    "industry": "Technology",        // ← Was ai_industry
    "companySize": "10001+",         // ← Was ai_company_size
    "digitalMaturity": "Advanced",   // ← Was ai_digital_maturity
    "targetAudience": "Businesses",  // ← Was ai_target_audience
    // ... all Layer 1 + 2 fields
  }
}
```

## Related Files

- **Backend (needs fix)**:
  - `app/routes/enrichment_progressive.py` - SSE stream endpoint
  - `app/services/enrichment/progressive_orchestrator.py` - Field extraction

- **Data Sources**:
  - `app/services/enrichment/sources/metadata.py` - Extracts `company_name`
  - `app/services/enrichment/sources/ip_api.py` - Extracts `city`, `region`
  - `app/services/enrichment/sources/clearbit.py` - Extracts `employee_count`
  - `app/services/ai/openrouter_client.py` - Extracts `ai_*` fields

- **Frontend (location unknown)**:
  - `components/progressive-enrichment-form.tsx` - Form field definitions
  - SSE event handler that receives `fields_auto_filled`
