"""
Repository Pattern Implementation
Provides clean abstraction layer for database operations
"""

from .base import BaseRepository, ReadOnlyRepository
from .supabase_repository import SupabaseRepository
from .submission_repository import (
    SubmissionRepository,
    submission_repository,
    get_submission_repository
)
from .enrichment_repository import (
    EnrichmentRepository,
    enrichment_repository,
    get_enrichment_repository
)
from .audit_repository import (
    AuditRepository,
    audit_repository,
    get_audit_repository
)
from . import progressive_enrichment_repository

__all__ = [
    "BaseRepository",
    "ReadOnlyRepository",
    "SupabaseRepository",
    "SubmissionRepository",
    "submission_repository",
    "get_submission_repository",
    "EnrichmentRepository",
    "enrichment_repository",
    "get_enrichment_repository",
    "AuditRepository",
    "audit_repository",
    "get_audit_repository",
    "progressive_enrichment_repository",
]
