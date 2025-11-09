"""
OpenAPI Schema Customization and Documentation Enhancement

This module provides custom OpenAPI schema generation with:
- Enhanced example request/response bodies
- Detailed security scheme documentation
- Common response models
- Tag descriptions with metadata
"""
from typing import Dict, Any, List
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


# ============================================================================
# EXAMPLE REQUEST/RESPONSE BODIES
# ============================================================================

EXAMPLES = {
    "submission_create": {
        "summary": "Complete Lead Submission",
        "description": "Full example with all fields for comprehensive analysis",
        "value": {
            "name": "João Silva",
            "email": "joao.silva@techcorp.com.br",
            "company": "TechCorp Solutions",
            "website": "https://techcorp.com.br",
            "linkedin_company": "https://linkedin.com/company/techcorp-solutions",
            "linkedin_founder": "https://linkedin.com/in/joao-silva-founder",
            "industry": "Tecnologia",
            "challenge": "Precisamos expandir nossa base de clientes B2B no setor financeiro"
        }
    },
    "submission_response": {
        "summary": "Successful Submission",
        "value": {
            "success": True,
            "submission_id": 42
        }
    },
    "login_request": {
        "summary": "Admin Login",
        "value": {
            "email": "admin@strategyai.com",
            "password": "SecurePassword123!"
        }
    },
    "login_response": {
        "summary": "Successful Login",
        "value": {
            "success": True,
            "data": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "user": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "email": "admin@strategyai.com"
                }
            }
        }
    },
    "sse_event": {
        "summary": "SSE Progress Event",
        "value": {
            "stage": "data_gathering",
            "message": "Coletando dados da empresa...",
            "progress": 30,
            "timestamp": "2025-01-26T10:30:00Z"
        }
    },
    "chat_request": {
        "summary": "Chat Message",
        "value": {
            "message": "Quais são os principais riscos identificados para esta empresa?",
            "model": "haiku"
        }
    },
    "chat_response": {
        "summary": "AI Chat Response",
        "value": {
            "success": True,
            "message": "Com base na análise, identifiquei 3 riscos principais...",
            "model_used": "claude-3-5-haiku-20241022",
            "tokens_used": 542,
            "timestamp": "2025-01-26T10:35:00Z",
            "chat_history": [
                {
                    "role": "user",
                    "content": "Quais são os principais riscos?"
                },
                {
                    "role": "assistant",
                    "content": "Com base na análise..."
                }
            ]
        }
    },
    "edit_request": {
        "summary": "Edit Report Section",
        "value": {
            "selected_text": "A empresa possui forte presença digital.",
            "section_path": "diagnostico_estrategico.forças[0]",
            "instruction": "Adicione métricas específicas de presença digital",
            "complexity": "simple"
        }
    },
    "health_check": {
        "summary": "Healthy System",
        "value": {
            "status": "healthy",
            "timestamp": "2025-01-26T10:00:00Z",
            "version": "2.0.0",
            "environment": "production",
            "checks": {
                "database": {
                    "status": "healthy",
                    "submissions_count": 1247
                },
                "redis": {
                    "status": "healthy"
                },
                "openrouter": {
                    "status": "configured",
                    "api_key_present": True
                },
                "circuit_breakers": {
                    "status": "healthy",
                    "summary": "All breakers closed",
                    "open_circuits": []
                }
            }
        }
    }
}


# ============================================================================
# ERROR RESPONSE EXAMPLES
# ============================================================================

ERROR_RESPONSES = {
    "400": {
        "description": "Bad Request - Invalid input data",
        "content": {
            "application/json": {
                "examples": {
                    "validation_error": {
                        "summary": "Validation Error",
                        "value": {
                            "detail": [
                                {
                                    "loc": ["body", "email"],
                                    "msg": "Please use a corporate email address",
                                    "type": "value_error"
                                }
                            ]
                        }
                    },
                    "challenge_too_long": {
                        "summary": "Challenge Too Long",
                        "value": {
                            "detail": [
                                {
                                    "loc": ["body", "challenge"],
                                    "msg": "Challenge must be maximum 200 characters",
                                    "type": "value_error"
                                }
                            ]
                        }
                    }
                }
            }
        }
    },
    "401": {
        "description": "Unauthorized - Invalid or expired token",
        "content": {
            "application/json": {
                "examples": {
                    "invalid_token": {
                        "summary": "Invalid Token",
                        "value": {
                            "detail": "Invalid or expired token"
                        }
                    },
                    "invalid_credentials": {
                        "summary": "Invalid Credentials",
                        "value": {
                            "success": False,
                            "error": "Invalid email or password"
                        }
                    }
                }
            }
        }
    },
    "403": {
        "description": "Forbidden - Insufficient permissions",
        "content": {
            "application/json": {
                "example": {
                    "detail": "Access denied. Admin privileges required."
                }
            }
        }
    },
    "404": {
        "description": "Not Found - Resource doesn't exist",
        "content": {
            "application/json": {
                "example": {
                    "detail": "Submission not found"
                }
            }
        }
    },
    "429": {
        "description": "Rate Limit Exceeded",
        "content": {
            "application/json": {
                "example": {
                    "detail": "Rate limit exceeded. Maximum 3 submissions per day.",
                    "retry_after": 43200
                }
            }
        }
    },
    "500": {
        "description": "Internal Server Error",
        "content": {
            "application/json": {
                "example": {
                    "detail": "An unexpected error occurred. Please try again later."
                }
            }
        }
    },
    "503": {
        "description": "Service Unavailable - Dependency failure",
        "content": {
            "application/json": {
                "example": {
                    "status": "unhealthy",
                    "timestamp": "2025-01-26T10:00:00Z",
                    "checks": {
                        "database": {
                            "status": "unhealthy",
                            "error": "Connection timeout"
                        }
                    }
                }
            }
        }
    }
}


# ============================================================================
# SECURITY SCHEMES
# ============================================================================

SECURITY_SCHEMES = {
    "BearerAuth": {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": """
JWT authentication for admin endpoints.

**How to obtain a token:**
1. Call POST /api/auth/login with email and password
2. Extract the `access_token` from the response
3. Use the token in the Authorization header: `Bearer <token>`

**Token Format:**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Token Expiration:** 7 days (configurable)

**Note:** Only users with admin privileges can authenticate.
        """
    }
}


# ============================================================================
# CUSTOM OPENAPI SCHEMA GENERATOR
# ============================================================================

def custom_openapi(app: FastAPI) -> Dict[str, Any]:
    """
    Generate custom OpenAPI schema with enhanced documentation.

    Args:
        app: FastAPI application instance

    Returns:
        Enhanced OpenAPI schema dictionary
    """
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        servers=app.servers,
        tags=app.openapi_tags,
        terms_of_service=app.terms_of_service,
        contact=app.contact,
        license_info=app.license_info,
    )

    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = SECURITY_SCHEMES

    # Add external documentation
    openapi_schema["externalDocs"] = {
        "description": "Strategy AI Documentation",
        "url": "https://docs.strategyai.example.com"
    }

    # Add common response schemas
    openapi_schema["components"]["schemas"]["ErrorResponse"] = {
        "type": "object",
        "properties": {
            "success": {
                "type": "boolean",
                "default": False
            },
            "error": {
                "type": "string",
                "description": "Error message"
            }
        }
    }

    openapi_schema["components"]["schemas"]["SuccessResponse"] = {
        "type": "object",
        "properties": {
            "success": {
                "type": "boolean",
                "default": True
            },
            "message": {
                "type": "string",
                "description": "Success message"
            }
        }
    }

    # Enhance path descriptions with examples
    for path, path_item in openapi_schema["paths"].items():
        for method, operation in path_item.items():
            if method in ["get", "post", "put", "patch", "delete"]:
                # Add common error responses
                if "responses" not in operation:
                    operation["responses"] = {}

                # Add security info to protected endpoints
                if "security" in operation:
                    operation["responses"]["401"] = ERROR_RESPONSES["401"]
                    operation["responses"]["403"] = ERROR_RESPONSES["403"]

                # Add 500 error to all endpoints
                operation["responses"]["500"] = ERROR_RESPONSES["500"]

    # Add info about rate limiting
    openapi_schema["info"]["x-rate-limit"] = {
        "description": "API implements rate limiting",
        "limits": {
            "public_submissions": "3 per IP per day",
            "authenticated_requests": "100 per minute"
        }
    }

    # Add API versioning info
    openapi_schema["info"]["x-api-version"] = {
        "current": "2.0.0",
        "supported": ["2.0.0"],
        "deprecated": []
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


# ============================================================================
# RESPONSE MODEL TEMPLATES
# ============================================================================

RESPONSE_MODELS = {
    "success_with_id": {
        "type": "object",
        "properties": {
            "success": {"type": "boolean", "example": True},
            "id": {"type": "integer", "example": 42}
        }
    },
    "success_with_message": {
        "type": "object",
        "properties": {
            "success": {"type": "boolean", "example": True},
            "message": {"type": "string", "example": "Operation completed successfully"}
        }
    },
    "paginated_response": {
        "type": "object",
        "properties": {
            "success": {"type": "boolean", "example": True},
            "data": {"type": "array", "items": {}},
            "total": {"type": "integer", "example": 100},
            "page": {"type": "integer", "example": 1},
            "page_size": {"type": "integer", "example": 20}
        }
    }
}


# ============================================================================
# AUTHENTICATION FLOW DOCUMENTATION
# ============================================================================

AUTHENTICATION_FLOW = """
## Authentication Flow

### 1. Sign Up (Optional)
```bash
POST /api/auth/signup
Content-Type: application/json

{
  "email": "admin@company.com",
  "password": "SecurePassword123!"
}
```

**Note:** New users don't have admin access by default. Admin privileges must be granted manually in Supabase.

### 2. Login
```bash
POST /api/auth/login
Content-Type: application/json

{
  "email": "admin@company.com",
  "password": "SecurePassword123!"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "user": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "admin@company.com"
    }
  }
}
```

### 3. Use Token in Requests
Include the token in the Authorization header for all protected endpoints:

```bash
GET /api/admin/submissions
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Token Lifecycle
- **Expiration:** 7 days (default)
- **Refresh:** Re-login to get a new token
- **Storage:** Store securely in httpOnly cookies or secure storage
"""


def get_authentication_documentation() -> str:
    """Get authentication flow documentation"""
    return AUTHENTICATION_FLOW
