from typing import Optional, Dict, Any
from datetime import datetime


class DCEBaseException(Exception):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.status_code = status_code
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "details": self.details
        }


class ContractError(DCEBaseException):
    pass


class DuplicateContractError(ContractError):
    def __init__(self, contract_name: str, details: Optional[Dict] = None):
        message = f"Contract with name '{contract_name}' already exists"
        super().__init__(
            message=message,
            details=details or {"contract_name": contract_name},
            status_code=409
        )


class ContractNotFoundError(ContractError):
    def __init__(self, contract_id: str, details: Optional[Dict] = None):
        message = f"Contract with ID '{contract_id}' not found"
        super().__init__(
            message=message,
            details=details or {"contract_id": contract_id},
            status_code=404
        )


class InvalidYAMLError(ContractError):
    def __init__(self, error_message: str, details: Optional[Dict] = None):
        message = f"Invalid YAML: {error_message}"
        super().__init__(
            message=message,
            details=details or {"yaml_error": error_message},
            status_code=400
        )


class InvalidContractSchemaError(ContractError):
    def __init__(self, error_message: str, details: Optional[Dict] = None):
        message = f"Invalid contract schema: {error_message}"
        super().__init__(
            message=message,
            details=details or {"schema_error": error_message},
            status_code=400
        )


class ContractInactiveError(ContractError):
    def __init__(self, contract_id: str, details: Optional[Dict] = None):
        message = f"Contract '{contract_id}' is inactive"
        super().__init__(
            message=message,
            details=details or {"contract_id": contract_id},
            status_code=400
        )


class ValidationError(DCEBaseException):
    pass


class SchemaValidationError(ValidationError):
    def __init__(self, contract_id: str, errors: list, details: Optional[Dict] = None):
        message = f"Schema validation failed with {len(errors)} error(s)"
        super().__init__(
            message=message,
            details=details or {
                "contract_id": contract_id,
                "error_count": len(errors),
                "errors": errors
            },
            status_code=422
        )


class QualityValidationError(ValidationError):
    def __init__(self, contract_id: str, errors: list, details: Optional[Dict] = None):
        message = f"Quality validation failed with {len(errors)} error(s)"
        super().__init__(
            message=message,
            details=details or {
                "contract_id": contract_id,
                "error_count": len(errors),
                "errors": errors
            },
            status_code=422
        )


class DatabaseError(DCEBaseException):
    def __init__(self, operation: str, error_message: str, details: Optional[Dict] = None):
        message = f"Database {operation} failed: {error_message}"
        super().__init__(
            message=message,
            details=details or {
                "operation": operation,
                "error": error_message
            },
            status_code=500
        )


class TransactionError(DatabaseError):
    def __init__(self, error_message: str, details: Optional[Dict] = None):
        super().__init__(
            operation="transaction",
            error_message=error_message,
            details=details
        )


class FileProcessingError(DCEBaseException):
    pass


class InvalidFileFormatError(FileProcessingError):
    def __init__(self, file_type: str, error_message: str, details: Optional[Dict] = None):
        message = f"Invalid {file_type} file format: {error_message}"
        super().__init__(
            message=message,
            details=details or {
                "file_type": file_type,
                "error": error_message
            },
            status_code=400
        )


class FileSizeLimitError(FileProcessingError):
    def __init__(self, file_size: int, max_size: int, details: Optional[Dict] = None):
        message = f"File size {file_size} bytes exceeds limit of {max_size} bytes"
        super().__init__(
            message=message,
            details=details or {
                "file_size": file_size,
                "max_size": max_size
            },
            status_code=413
        )


class BatchProcessingError(FileProcessingError):
    def __init__(self, batch_id: str, error_message: str, details: Optional[Dict] = None):
        message = f"Batch {batch_id} processing failed: {error_message}"
        super().__init__(
            message=message,
            details=details or {
                "batch_id": batch_id,
                "error": error_message
            },
            status_code=500
        )


class VersioningError(DCEBaseException):
    pass


class VersionNotFoundError(VersioningError):
    def __init__(self, contract_id: str, version: str, details: Optional[Dict] = None):
        message = f"Version '{version}' not found for contract '{contract_id}'"
        super().__init__(
            message=message,
            details=details or {
                "contract_id": contract_id,
                "version": version
            },
            status_code=404
        )


class InvalidVersionError(VersioningError):
    def __init__(self, version: str, details: Optional[Dict] = None):
        message = f"Invalid version format: '{version}'"
        super().__init__(
            message=message,
            details=details or {"version": version},
            status_code=400
        )


class AuthorizationError(DCEBaseException):
    pass


class InsufficientPermissionsError(AuthorizationError):
    def __init__(self, operation: str, details: Optional[Dict] = None):
        message = f"Insufficient permissions for operation: {operation}"
        super().__init__(
            message=message,
            details=details or {"operation": operation},
            status_code=403
        )


class AuthenticationRequiredError(AuthorizationError):
    def __init__(self, details: Optional[Dict] = None):
        message = "Authentication is required for this operation"
        super().__init__(
            message=message,
            details=details,
            status_code=401
        )


# ============ NEW EXCEPTIONS ADDED BELOW ============


class UnsupportedFileFormatError(DCEBaseException):
    """Raised when an unsupported file format is provided."""
    def __init__(self, file_type: str, supported_formats: list, details: Optional[Dict] = None):
        message = f"Unsupported file format: '{file_type}'. Supported formats: {', '.join(supported_formats)}"
        super().__init__(
            message=message,
            details=details or {
                "file_type": file_type,
                "supported_formats": supported_formats
            },
            status_code=415  # Unsupported Media Type
        )


class FileTooLargeError(DCEBaseException):
    """Raised when a file exceeds the maximum allowed size."""
    def __init__(self, file_size: int, max_size: int, details: Optional[Dict] = None):
        message = f"File size ({file_size} bytes) exceeds maximum allowed size ({max_size} bytes)"
        super().__init__(
            message=message,
            details=details or {
                "file_size": file_size,
                "max_size": max_size,
                "max_size_mb": max_size / (1024 * 1024)
            },
            status_code=413  # Payload Too Large
        )


class BatchJobError(DCEBaseException):
    """Raised when a batch job encounters an error."""
    def __init__(self, batch_id: str, stage: str, error_message: str, details: Optional[Dict] = None):
        message = f"Batch job '{batch_id}' failed at stage '{stage}': {error_message}"
        super().__init__(
            message=message,
            details=details or {
                "batch_id": batch_id,
                "stage": stage,
                "error": error_message
            },
            status_code=500
        )


class MetricsError(DCEBaseException):
    """Raised when metrics calculation or retrieval fails."""
    def __init__(self, operation: str, error_message: str, details: Optional[Dict] = None):
        message = f"Metrics {operation} failed: {error_message}"
        super().__init__(
            message=message,
            details=details or {
                "operation": operation,
                "error": error_message
            },
            status_code=500
        )


class SchedulerError(DCEBaseException):
    """Raised when scheduler operations fail."""
    def __init__(self, operation: str, error_message: str, details: Optional[Dict] = None):
        message = f"Scheduler {operation} failed: {error_message}"
        super().__init__(
            message=message,
            details=details or {
                "operation": operation,
                "error": error_message
            },
            status_code=500
        )


def get_http_status_code(exception: Exception) -> int:
    """Get the HTTP status code for an exception."""
    if isinstance(exception, DCEBaseException):
        return exception.status_code
    return 500


def format_error_response(exception: Exception, path: Optional[str] = None) -> Dict[str, Any]:
    """Format an exception into a standard error response."""
    if isinstance(exception, DCEBaseException):
        response = exception.to_dict()
    else:
        response = {
            "error": exception.__class__.__name__,
            "message": str(exception),
            "details": {}
        }
    
    response["timestamp"] = datetime.utcnow().isoformat()
    
    if path:
        response["path"] = path
    
    return response