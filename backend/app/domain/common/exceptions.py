class DomainError(Exception):
    """Base exception for domain-level errors."""


class ValidationError(DomainError):
    """Raised when domain validation fails."""


class ConcurrencyError(DomainError):
    """Raised when concurrent modifications cannot be resolved."""
