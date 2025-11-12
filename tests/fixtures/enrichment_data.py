"""
Test fixtures for enrichment functionality
Provides sample company data for testing progressive enrichment layers
"""
from typing import Dict, Any

# Sample companies for testing
SAMPLE_COMPANIES = {
    "vallente": {
        "url": "https://vallenteclinic.com.br",
        "expected": {
            "company_name": "Vallente Clinic",
            "industry": "Healthcare",
            "description": "Aesthetic and wellness clinic",
            "instagram": "@vallenteclinic",
            "location": "Brazil",
            "phone": "+55 11 98765-4321",
            "confidence_scores": {
                "company_name": 0.95,
                "industry": 0.90,
                "description": 0.85
            }
        },
        "layer1_metadata": {
            "title": "Vallente Clinic - Aesthetic Treatments",
            "meta_description": "Leading aesthetic clinic in Brazil",
            "og_image": "https://vallenteclinic.com.br/og-image.jpg",
            "social_links": ["https://instagram.com/vallenteclinic"]
        },
        "layer2_clearbit": {
            "name": "Vallente Clinic",
            "domain": "vallenteclinic.com.br",
            "category": {
                "industry": "Healthcare"
            }
        }
    },
    "imensiah": {
        "url": "https://imensiah.com.br",
        "expected": {
            "company_name": "IMENSIAH",
            "industry": "Technology / AI",
            "description": "Intelligent form enrichment platform",
            "location": "Brazil",
            "confidence_scores": {
                "company_name": 0.98,
                "industry": 0.92,
                "description": 0.88
            }
        },
        "layer1_metadata": {
            "title": "IMENSIAH - Intelligent Form Enrichment",
            "meta_description": "AI-powered form enrichment for better data",
            "social_links": []
        }
    },
    "test_startup": {
        "url": "https://teststartup.com",
        "expected": {
            "company_name": "Test Startup",
            "industry": "Software",
            "description": "Innovative software solutions",
            "confidence_scores": {
                "company_name": 0.85,
                "industry": 0.80,
                "description": 0.75
            }
        },
        "layer1_metadata": {
            "title": "Test Startup",
            "meta_description": "We build software",
            "social_links": ["https://linkedin.com/company/test-startup"]
        }
    },
    "br_ecommerce": {
        "url": "https://lojaexemplo.com.br",
        "cnpj": "12.345.678/0001-90",
        "expected": {
            "company_name": "Loja Exemplo Ltda",
            "industry": "E-commerce",
            "description": "Online retail store",
            "location": "São Paulo, SP",
            "phone": "+55 11 3456-7890",
            "confidence_scores": {
                "company_name": 0.99,
                "industry": 0.85,
                "location": 0.95
            }
        },
        "layer2_receitaws": {
            "nome": "LOJA EXEMPLO LTDA",
            "fantasia": "Loja Exemplo",
            "uf": "SP",
            "municipio": "SÃO PAULO",
            "telefone": "(11) 3456-7890",
            "atividade_principal": [
                {
                    "text": "Comércio varejista pela internet",
                    "code": "47.81-4-00"
                }
            ]
        }
    }
}

# Social media test data
SOCIAL_MEDIA_TESTS = {
    "instagram": {
        "handles": [
            ("@vallenteclinic", "https://instagram.com/vallenteclinic"),
            ("vallenteclinic", "https://instagram.com/vallenteclinic"),
            ("https://instagram.com/vallenteclinic", "https://instagram.com/vallenteclinic"),
            ("https://www.instagram.com/vallenteclinic/", "https://instagram.com/vallenteclinic")
        ]
    },
    "tiktok": {
        "handles": [
            ("@testuser", "https://tiktok.com/@testuser"),
            ("testuser", "https://tiktok.com/@testuser"),
            ("https://tiktok.com/@testuser", "https://tiktok.com/@testuser")
        ]
    },
    "linkedin": {
        "company_urls": [
            ("test-company", "https://linkedin.com/company/test-company"),
            ("https://linkedin.com/company/test-company", "https://linkedin.com/company/test-company"),
            ("https://www.linkedin.com/company/test-company/", "https://linkedin.com/company/test-company")
        ]
    }
}

# Phone number test data
PHONE_TESTS = {
    "brazilian": [
        ("11987654321", "+55 11 98765-4321"),
        ("11 98765-4321", "+55 11 98765-4321"),
        ("+55 11 98765-4321", "+55 11 98765-4321"),
        ("(11) 98765-4321", "+55 11 98765-4321"),
        ("+5511987654321", "+55 11 98765-4321")
    ],
    "whatsapp": [
        ("5511987654321", "+55 11 98765-4321"),
        ("https://wa.me/5511987654321", "+55 11 98765-4321")
    ]
}

# URL test data
URL_TESTS = {
    "auto_prefix": [
        ("example.com", "https://example.com"),
        ("www.example.com", "https://www.example.com"),
        ("http://example.com", "http://example.com"),
        ("https://example.com", "https://example.com"),
        ("ftp://example.com", "ftp://example.com")
    ],
    "validation": {
        "valid": [
            "https://example.com",
            "https://subdomain.example.com",
            "https://example.com/path",
            "https://example.com:8080"
        ],
        "invalid": [
            "not a url",
            "htp://broken.com",
            "javascript:alert(1)",
            ""
        ]
    }
}

# Error scenarios
ERROR_SCENARIOS = {
    "invalid_urls": [
        "not-a-url",
        "http://",
        "https://",
        "ftp://invalid",
        ""
    ],
    "timeout": {
        "url": "https://timeout-simulator.example.com",
        "expected_fallback": True
    },
    "rate_limit": {
        "url": "https://rate-limited.example.com",
        "expected_status": 429
    },
    "api_failures": {
        "clearbit": {"status": 404, "message": "Company not found"},
        "receitaws": {"status": 500, "message": "Service unavailable"},
        "openai": {"status": 429, "message": "Rate limit exceeded"}
    }
}

# Performance benchmarks
PERFORMANCE_BENCHMARKS = {
    "layer1": {
        "max_duration_seconds": 2.0,
        "operations": ["metadata_extraction", "social_detection"]
    },
    "layer2": {
        "max_duration_seconds": 6.0,
        "operations": ["clearbit_lookup", "receitaws_lookup", "data_reconciliation"]
    },
    "layer3": {
        "max_duration_seconds": 10.0,
        "operations": ["ai_inference", "confidence_scoring"]
    },
    "total": {
        "max_duration_seconds": 15.0
    }
}

# Expected field mapping
FIELD_MAPPINGS = {
    "frontend_to_backend": {
        "website": "url",
        "company_name": "company_name",
        "industry": "industry",
        "description": "description",
        "instagram": "instagram",
        "tiktok": "tiktok",
        "linkedin": "linkedin_company",
        "phone": "phone",
        "whatsapp": "whatsapp"
    },
    "backend_to_frontend": {
        "url": "website",
        "company_name": "company_name",
        "industry": "industry",
        "description": "description",
        "instagram": "instagram",
        "tiktok": "tiktok",
        "linkedin_company": "linkedin",
        "phone": "phone",
        "whatsapp": "whatsapp"
    }
}

# Confidence score thresholds
CONFIDENCE_THRESHOLDS = {
    "high": 0.85,
    "medium": 0.65,
    "low": 0.45,
    "minimum_acceptable": 0.40
}
