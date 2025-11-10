# Bugs Found in Production API Testing

**Date**: 2025-11-10
**Test Environment**: Production (Railway)

---

## Critical Bugs (3)

### 🔴 Bug #1: Layer 1 Missing 9+ Fields

**Severity**: HIGH
**Status**: Confirmed
**Impact**: Users must manually enter 9+ fields instead of auto-fill

**Description**:
Layer 1 (Metadata + IP-API) only returns 2 fields (name, websiteTech) instead of 11+ expected fields.

**Missing Fields**:
- state (from region)
- city
- country
- countryName
- timezone
- ipAddress
- ipLocation
- description
- metaDescription
- logoUrl

**Evidence**:
```json
{
  "fields_auto_filled": {
    "name": "Google",
    "websiteTech": ["Angular"]
    // MISSING 9 fields from Layer 1
  }
}
```

**Root Cause**: IP-API source likely failing silently or not being called.

**Fix**: Check `app/services/enrichment/sources/ip_api.py` and progressive orchestrator Layer 1 execution.

---

### 🔴 Bug #2: SSE Stream Times Out

**Severity**: CRITICAL
**Status**: Confirmed
**Impact**: Frontend cannot receive progressive updates, form doesn't auto-fill in real-time

**Description**:
SSE stream endpoint hangs and times out after 30 seconds without sending any events.

**Evidence**:
```
HTTPSConnectionPool(host='web-production-c5845.up.railway.app', port=443):
Read timed out. (read timeout=30)
```

**Root Cause**: SSE generator may be blocking, or session not found, or no keepalive pings.

**Fix**: Add keepalive pings, timeout handling in SSE stream generator.

---

### 🟡 Bug #3: Layer Completion Flags Missing

**Severity**: MEDIUM
**Status**: Confirmed
**Impact**: Cannot debug layer execution, no visibility into what layers ran

**Description**:
Session endpoint returns `None` for all layer completion flags.

**Expected**:
```json
{
  "layer1_complete": true,
  "layer2_complete": false,
  "layer3_complete": true
}
```

**Actual**:
```json
{
  "layer1_complete": null,
  "layer2_complete": null,
  "layer3_complete": null
}
```

**Fix**: Add boolean flags to ProgressiveEnrichmentSession model.

---

## Minor Issues (2)

### 🟡 Issue #1: Confidence Scores Not Translated

**Severity**: LOW
**Impact**: Frontend cannot map confidence scores to fields

**Description**:
Confidence scores use backend field names (company_name, ai_industry) instead of frontend field names (name, industry).

**Evidence**:
```json
{
  "confidence_scores": {
    "company_name": 70.0,     // Should be "name"
    "ai_industry": 75.0        // Should be "industry"
  }
}
```

**Fix**: Apply `translate_fields_for_frontend()` to confidence_scores.

---

### 🟡 Issue #2: AI Responses in Portuguese

**Severity**: LOW
**Impact**: Minor UX issue

**Description**:
AI generates fields in Portuguese instead of English.

**Evidence**:
```json
{
  "industry": "Tecnologia",           // Should be "Technology"
  "companySize": "Grande",            // Should be "Large"
  "digitalMaturity": "Alta"           // Should be "High"
}
```

**Fix**: Update AI prompt to specify English responses.

---

## Test Results Summary

| Test | Status | Critical Issues |
|------|--------|----------------|
| Layer 1 (Metadata + IP-API) | ❌ FAILED | Missing 9+ fields |
| Layer 2 (Paid APIs) | ❌ FAILED | No layer flags |
| Layer 3 (AI + LinkedIn) | ✅ PASSED | None |
| SSE Stream | ❌ ERROR | Timeout |
| Complete E2E Flow | ⚠️ PARTIAL | Only 7/16+ fields |

**Pass Rate**: 20% (1/5 tests passed)

---

## Recommended Fix Priority

1. **P0**: Fix Layer 1 missing fields (blocks adoption)
2. **P0**: Fix SSE stream timeout (breaks UX)
3. **P1**: Add layer completion flags (improves debugging)
4. **P2**: Translate confidence scores (improves UX)
5. **P3**: Fix AI language to English (minor polish)

---

## Files to Fix

1. `app/services/enrichment/sources/ip_api.py` - IP geolocation
2. `app/services/enrichment/progressive_orchestrator.py` - Layer execution
3. `app/routes/enrichment_progressive.py` - SSE stream + layer flags
4. `app/services/enrichment/progressive_orchestrator.py` - Session model

---

## Full Report

See: `docs/E2E_PRODUCTION_TEST_REPORT.md`
