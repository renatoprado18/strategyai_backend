# Progressive Enrichment API - Quick Reference

## Base URL
```
https://api.strategyai.com
```

## Authentication
Admin endpoints require JWT token in Authorization header:
```
Authorization: Bearer <token>
```

---

## Phase 2 - Admin Transparency

### List Sessions
```http
GET /api/enrichment/admin/sessions?limit=20&offset=0&status=complete
Authorization: Bearer <admin_token>
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "session_id": "uuid",
      "website_url": "https://example.com",
      "status": "complete",
      "total_cost_usd": 0.25,
      "total_duration_ms": 5400
    }
  ],
  "metadata": {
    "timestamp": "2025-01-09T10:00:00Z",
    "query_time_ms": 45,
    "total_count": 150,
    "page": 1,
    "limit": 20
  }
}
```

### Get Session Detail
```http
GET /api/enrichment/admin/sessions/{session_id}
Authorization: Bearer <admin_token>
```

### Get Field Attribution
```http
GET /api/enrichment/admin/sessions/{session_id}/attribution
Authorization: Bearer <admin_token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "session_id": "uuid",
    "attribution": {
      "company_name": {
        "source": "Clearbit",
        "layer": 2,
        "confidence": 95.0,
        "was_accepted": true,
        "was_edited": false
      },
      "industry": {
        "source": "AI inference",
        "layer": 3,
        "confidence": 88.5,
        "was_accepted": true,
        "was_edited": true
      }
    },
    "total_fields": 12
  }
}
```

---

## Phase 5 - Analytics

### Overview Analytics
```http
GET /api/enrichment/analytics/overview?days=30
Authorization: Bearer <admin_token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "period_days": 30,
    "total_sessions": 1247,
    "total_cost_usd": 312.50,
    "avg_duration_ms": 4850,
    "status_distribution": {
      "complete": 1100,
      "pending": 50,
      "error": 97
    },
    "layer_completion": {
      "layer1": 1247,
      "layer2": 1180,
      "layer3": 1100
    },
    "completion_rates": {
      "layer1_pct": 100.0,
      "layer2_pct": 94.6,
      "layer3_pct": 88.2
    }
  },
  "metadata": {
    "timestamp": "2025-01-09T10:00:00Z",
    "query_time_ms": 156
  }
}
```

### Cost Analytics
```http
GET /api/enrichment/analytics/costs?days=30
Authorization: Bearer <admin_token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "period_days": 30,
    "total_cost_usd": 312.5000,
    "avg_daily_cost_usd": 10.4167,
    "daily_trend": [
      {"date": "2024-12-10", "cost_usd": 9.2500},
      {"date": "2024-12-11", "cost_usd": 11.5000}
    ],
    "source_breakdown": [
      {"source": "Clearbit", "total_cost_usd": 125.0000},
      {"source": "LinkedIn API", "total_cost_usd": 98.7500},
      {"source": "Google Places", "total_cost_usd": 45.5000}
    ]
  }
}
```

### Performance Analytics
```http
GET /api/enrichment/analytics/performance?days=30
Authorization: Bearer <admin_token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "period_days": 30,
    "total_sessions": 1247,
    "layer_metrics": {
      "layer1": {
        "avg_duration_ms": 450,
        "min_duration_ms": 280,
        "max_duration_ms": 1200,
        "avg_cost_usd": 0.000000,
        "completion_count": 1247,
        "completion_rate_pct": 100.0
      },
      "layer2": {
        "avg_duration_ms": 2800,
        "min_duration_ms": 1800,
        "max_duration_ms": 5400,
        "avg_cost_usd": 0.150000,
        "completion_count": 1180,
        "completion_rate_pct": 94.6
      },
      "layer3": {
        "avg_duration_ms": 1600,
        "min_duration_ms": 800,
        "max_duration_ms": 3200,
        "avg_cost_usd": 0.100000,
        "completion_count": 1100,
        "completion_rate_pct": 88.2
      }
    }
  }
}
```

### Field Analytics
```http
GET /api/enrichment/analytics/fields?days=30
Authorization: Bearer <admin_token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "period_days": 30,
    "total_fields": 15,
    "fields": [
      {
        "field_name": "company_name",
        "total_suggestions": 1247,
        "accepted_count": 1180,
        "edited_count": 67,
        "auto_filled_count": 1100,
        "acceptance_rate_pct": 94.6,
        "edit_rate_pct": 5.4,
        "auto_fill_rate_pct": 88.2,
        "avg_confidence": 92.3
      },
      {
        "field_name": "industry",
        "total_suggestions": 1247,
        "accepted_count": 950,
        "edited_count": 297,
        "auto_filled_count": 800,
        "acceptance_rate_pct": 76.2,
        "edit_rate_pct": 23.8,
        "auto_fill_rate_pct": 64.2,
        "avg_confidence": 78.5
      }
    ]
  }
}
```

### Cache Analytics
```http
GET /api/enrichment/analytics/cache?days=30
Authorization: Bearer <admin_token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "period_days": 30,
    "total_cache_entries": 450,
    "valid_entries": 387,
    "validation_rate_pct": 86.0,
    "platform_stats": [
      {
        "platform": "instagram",
        "total_validations": 180,
        "valid_count": 165,
        "validation_rate_pct": 91.7
      },
      {
        "platform": "linkedin",
        "total_validations": 150,
        "valid_count": 138,
        "validation_rate_pct": 92.0
      },
      {
        "platform": "tiktok",
        "total_validations": 120,
        "valid_count": 84,
        "validation_rate_pct": 70.0
      }
    ]
  }
}
```

---

## Phase 6 - User Edit Tracking

### Track User Edit (PUBLIC - No Auth)
```http
POST /api/enrichment/sessions/{session_id}/edit
Content-Type: application/json

{
  "field_name": "company_name",
  "original_value": "TechStart Inc",
  "edited_value": "TechStart Innovations",
  "confidence": 92.5
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "success": true,
    "message": "Edit tracked successfully",
    "field_name": "company_name",
    "confidence_adjustment": -5.0
  },
  "metadata": {
    "timestamp": "2025-01-09T10:00:00Z",
    "query_time_ms": 28
  }
}
```

### Get Learning Patterns
```http
GET /api/enrichment/learning/patterns?days=30
Authorization: Bearer <admin_token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "period_days": 30,
    "total_fields_analyzed": 15,
    "insights": [
      {
        "field_name": "industry",
        "total_interactions": 500,
        "edit_rate_pct": 35.2,
        "accept_rate_pct": 64.8,
        "avg_confidence": 78.5,
        "high_confidence_edits": 58,
        "recommended_confidence_threshold": 70,
        "needs_improvement": true
      },
      {
        "field_name": "company_name",
        "total_interactions": 500,
        "edit_rate_pct": 8.4,
        "accept_rate_pct": 91.6,
        "avg_confidence": 94.2,
        "high_confidence_edits": 5,
        "recommended_confidence_threshold": 84,
        "needs_improvement": false
      }
    ]
  },
  "metadata": {
    "timestamp": "2025-01-09T10:00:00Z",
    "query_time_ms": 187
  }
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid input: field_name is required"
}
```

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

### 403 Forbidden
```json
{
  "detail": "Admin privileges required"
}
```

### 404 Not Found
```json
{
  "detail": "Session 123e4567-e89b-12d3-a456-426614174000 not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Failed to get session detail: Database connection error"
}
```

---

## Common Query Parameters

| Parameter | Type | Default | Max | Description |
|-----------|------|---------|-----|-------------|
| `days` | int | 30 | 90 | Number of days to analyze |
| `limit` | int | 20 | 100 | Records per page |
| `offset` | int | 0 | - | Pagination offset |
| `status` | string | - | - | Filter by status |

---

## Response Time Guidelines

- Simple queries: < 100ms
- Analytics queries: < 500ms
- Complex aggregations: < 1000ms

All responses include `query_time_ms` in metadata for monitoring.

---

## Rate Limiting

- Admin endpoints: 100 requests/minute per user
- Public endpoints: 10 requests/minute per IP
- Burst: 20 requests allowed

---

## Pagination

For paginated endpoints (e.g., `/sessions`):

```
Page 1: ?limit=20&offset=0
Page 2: ?limit=20&offset=20
Page 3: ?limit=20&offset=40
```

Metadata includes:
- `total_count`: Total records available
- `page`: Current page number
- `limit`: Records per page

---

## Testing with cURL

### Admin Endpoint
```bash
curl -X GET "https://api.strategyai.com/api/enrichment/analytics/overview?days=30" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Public Endpoint
```bash
curl -X POST "https://api.strategyai.com/api/enrichment/sessions/123e4567-e89b-12d3-a456-426614174000/edit" \
  -H "Content-Type: application/json" \
  -d '{
    "field_name": "company_name",
    "original_value": "TechStart Inc",
    "edited_value": "TechStart Innovations",
    "confidence": 92.5
  }'
```

---

## OpenAPI Documentation

Full interactive API documentation available at:
- **Swagger UI:** https://api.strategyai.com/docs
- **ReDoc:** https://api.strategyai.com/redoc
- **OpenAPI Spec:** https://api.strategyai.com/openapi.json
