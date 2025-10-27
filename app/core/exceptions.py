"""
Custom Exception Classes for Strategy AI Backend
Provides domain-specific exceptions with proper status codes
"""
from typing import Any, Dict, Optional


class AppException(Exception):
    """
    Base exception class for all application exceptions

    Attributes:
        message: Human-readable error message
        status_code: HTTP status code
        details: Optional additional error details
    """

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON response"""
        return {
            "success": False,
            "error": self.message,
            "details": self.details
        }


# ============================================================================
# AUTHENTICATION & AUTHORIZATION EXCEPTIONS
# ============================================================================

class AuthenticationError(AppException):
    """Invalid credentials or authentication failure"""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401)


class InvalidCredentials(AuthenticationError):
    """Invalid email or password"""

    def __init__(self):
        super().__init__("Invalid email or password")


class TokenExpired(AuthenticationError):
    """JWT token has expired"""

    def __init__(self):
        super().__init__("Authentication token has expired")


class InvalidToken(AuthenticationError):
    """JWT token is invalid"""

    def __init__(self):
        super().__init__("Invalid authentication token")


class Unauthorized(AppException):
    """User does not have permission to access resource"""

    def __init__(self, message: str = "Unauthorized access"):
        super().__init__(message, status_code=403)


# ============================================================================
# RATE LIMITING EXCEPTIONS
# ============================================================================

class RateLimitExceeded(AppException):
    """Rate limit exceeded for this IP address"""

    def __init__(self, retry_after: Optional[int] = None):
        message = "Rate limit exceeded. Please try again later."
        details = {}
        if retry_after:
            details["retry_after_seconds"] = retry_after
            message = f"Rate limit exceeded. Please try again in {retry_after} seconds."

        super().__init__(message, status_code=429, details=details)


# ============================================================================
# RESOURCE NOT FOUND EXCEPTIONS
# ============================================================================

class ResourceNotFound(AppException):
    """Base class for resource not found errors"""

    def __init__(self, resource_type: str, resource_id: Any):
        message = f"{resource_type} with ID {resource_id} not found"
        super().__init__(message, status_code=404, details={
            "resource_type": resource_type,
            "resource_id": str(resource_id)
        })


class AnalysisNotFound(ResourceNotFound):
    """Analysis/submission not found"""

    def __init__(self, submission_id: int):
        super().__init__("Analysis", submission_id)


class ReportNotFound(ResourceNotFound):
    """Report not found"""

    def __init__(self, report_id: int):
        super().__init__("Report", report_id)


class UserNotFound(ResourceNotFound):
    """User not found"""

    def __init__(self, user_id: str):
        super().__init__("User", user_id)


# ============================================================================
# VALIDATION EXCEPTIONS
# ============================================================================

class ValidationError(AppException):
    """Input validation failed"""

    def __init__(self, message: str, field: Optional[str] = None):
        details = {}
        if field:
            details["field"] = field

        super().__init__(message, status_code=422, details=details)


class InvalidEmail(ValidationError):
    """Invalid email format or domain"""

    def __init__(self, email: str, reason: str = "Invalid email format"):
        super().__init__(f"{reason}: {email}", field="email")


class CorporateEmailRequired(ValidationError):
    """Corporate email required (no free email providers)"""

    def __init__(self, email: str):
        super().__init__(
            f"Corporate email required. Free email providers not allowed: {email}",
            field="email"
        )


class InvalidWebsite(ValidationError):
    """Invalid website URL"""

    def __init__(self, website: str):
        super().__init__(f"Invalid website URL: {website}", field="website")


class MissingRequiredField(ValidationError):
    """Required field is missing"""

    def __init__(self, field_name: str):
        super().__init__(f"Required field missing: {field_name}", field=field_name)


# ============================================================================
# ANALYSIS & PROCESSING EXCEPTIONS
# ============================================================================

class AnalysisError(AppException):
    """Base class for analysis-related errors"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=500, details=details)


class InsufficientData(AnalysisError):
    """Insufficient data to perform analysis"""

    def __init__(self, reason: str, missing_data: Optional[list] = None):
        details = {"reason": reason}
        if missing_data:
            details["missing_data"] = missing_data

        super().__init__(
            f"Insufficient data for analysis: {reason}",
            details=details
        )


class AnalysisTimeout(AnalysisError):
    """Analysis exceeded timeout limit"""

    def __init__(self, timeout_seconds: int):
        super().__init__(
            f"Analysis timed out after {timeout_seconds} seconds",
            details={"timeout_seconds": timeout_seconds}
        )


class AnalysisInProgress(AppException):
    """Analysis is still in progress"""

    def __init__(self, submission_id: int, status: str):
        super().__init__(
            f"Analysis {submission_id} is still in progress (status: {status})",
            status_code=202,
            details={"submission_id": submission_id, "status": status}
        )


class AnalysisFailed(AnalysisError):
    """Analysis failed"""

    def __init__(self, submission_id: int, error_message: str):
        super().__init__(
            f"Analysis {submission_id} failed: {error_message}",
            details={"submission_id": submission_id, "error": error_message}
        )


# ============================================================================
# EXTERNAL SERVICE EXCEPTIONS
# ============================================================================

class ExternalServiceError(AppException):
    """Base class for external service errors"""

    def __init__(self, service_name: str, message: str):
        super().__init__(
            f"{service_name} error: {message}",
            status_code=502,
            details={"service": service_name}
        )


class OpenRouterError(ExternalServiceError):
    """OpenRouter API error"""

    def __init__(self, message: str):
        super().__init__("OpenRouter", message)


class PerplexityError(ExternalServiceError):
    """Perplexity API error"""

    def __init__(self, message: str):
        super().__init__("Perplexity", message)


class ApifyError(ExternalServiceError):
    """Apify API error"""

    def __init__(self, message: str):
        super().__init__("Apify", message)


class SupabaseError(ExternalServiceError):
    """Supabase API error"""

    def __init__(self, message: str):
        super().__init__("Supabase", message)


class RedisError(ExternalServiceError):
    """Redis/Upstash error"""

    def __init__(self, message: str):
        super().__init__("Redis", message)


# ============================================================================
# PDF GENERATION EXCEPTIONS
# ============================================================================

class PDFGenerationError(AppException):
    """PDF generation failed"""

    def __init__(self, reason: str):
        super().__init__(
            f"Failed to generate PDF: {reason}",
            status_code=500,
            details={"reason": reason}
        )


# ============================================================================
# EDITING EXCEPTIONS
# ============================================================================

class EditError(AppException):
    """Base class for editing errors"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=400, details=details)


class InvalidEditPath(EditError):
    """Invalid JSON path for editing"""

    def __init__(self, path: str):
        super().__init__(
            f"Invalid edit path: {path}",
            details={"path": path}
        )


class EditValidationFailed(EditError):
    """Edit validation failed"""

    def __init__(self, reason: str):
        super().__init__(f"Edit validation failed: {reason}")


# ============================================================================
# DATABASE EXCEPTIONS
# ============================================================================

class DatabaseError(AppException):
    """Database operation failed"""

    def __init__(self, operation: str, error: str):
        super().__init__(
            f"Database {operation} failed: {error}",
            status_code=500,
            details={"operation": operation, "error": error}
        )


class DuplicateEntry(DatabaseError):
    """Duplicate entry in database"""

    def __init__(self, field: str, value: str):
        super().__init__(
            "insert",
            f"Duplicate entry for {field}: {value}"
        )
        self.status_code = 409  # Conflict


# ============================================================================
# CONFIGURATION EXCEPTIONS
# ============================================================================

class ConfigurationError(AppException):
    """Configuration error (missing env vars, invalid config, etc.)"""

    def __init__(self, message: str):
        super().__init__(f"Configuration error: {message}", status_code=500)


class MissingEnvironmentVariable(ConfigurationError):
    """Required environment variable is missing"""

    def __init__(self, var_name: str):
        super().__init__(f"Missing required environment variable: {var_name}")
