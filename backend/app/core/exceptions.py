"""Application-wide HTTP exceptions."""

from fastapi import HTTPException, status


class FieldIQError(HTTPException):
    """Base application error with structured detail."""

    def __init__(self, message: str, code: str, status_code: int = 400):
        super().__init__(
            status_code=status_code,
            detail={"error": message, "code": code},
        )


class NotFoundError(FieldIQError):
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            f"{resource} '{identifier}' not found",
            code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class InsufficientCreditsError(FieldIQError):
    def __init__(self, required: int, remaining: int):
        super().__init__(
            f"Insufficient credits: need {required}, have {remaining}",
            code="INSUFFICIENT_CREDITS",
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
        )


class RateLimitError(FieldIQError):
    def __init__(self, retry_after: int = 60):
        super().__init__(
            f"Rate limit exceeded. Retry after {retry_after}s",
            code="RATE_LIMIT",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )
