"""Custom exception classes for Naver-Logen integration."""

from typing import Optional


class NaverAPIError(Exception):
    """
    Exception raised for API-related errors.
    
    This includes authentication failures, network errors, server errors,
    and other issues when communicating with the Naver Commerce API.
    
    Attributes:
        message: Explanation of the error
        status_code: HTTP status code if applicable
        response_body: API response body if available
    """
    
    def __init__(self, message: str, status_code: Optional[int] = None, response_body: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(self.message)
    
    def __str__(self):
        error_parts = [self.message]
        if self.status_code:
            error_parts.append(f"Status Code: {self.status_code}")
        if self.response_body:
            error_parts.append(f"Response: {self.response_body}")
        return " | ".join(error_parts)


class DataTransformError(Exception):
    """
    Exception raised for data transformation and validation errors.
    
    This includes missing required fields, invalid data types, and
    malformed data that cannot be processed during transformation
    from Naver order format to Logen delivery format.
    
    Attributes:
        message: Explanation of the error
        order_id: ID of the order that caused the error
        missing_field: Name of the missing or invalid field
    """
    
    def __init__(self, message: str, order_id: Optional[str] = None, missing_field: Optional[str] = None):
        self.message = message
        self.order_id = order_id
        self.missing_field = missing_field
        super().__init__(self.message)
    
    def __str__(self):
        error_parts = [self.message]
        if self.order_id:
            error_parts.append(f"Order ID: {self.order_id}")
        if self.missing_field:
            error_parts.append(f"Missing Field: {self.missing_field}")
        return " | ".join(error_parts)


class ExcelGenerationError(Exception):
    """
    Exception raised for Excel file generation errors.
    
    This includes file system permission issues, disk space problems,
    invalid file paths, and openpyxl library errors.
    
    Attributes:
        message: Explanation of the error
        file_path: Path where the Excel file was being created
        underlying_error: The original exception that caused this error
    """
    
    def __init__(self, message: str, file_path: Optional[str] = None, underlying_error: Optional[Exception] = None):
        self.message = message
        self.file_path = file_path
        self.underlying_error = underlying_error
        super().__init__(self.message)
    
    def __str__(self):
        error_parts = [self.message]
        if self.file_path:
            error_parts.append(f"File Path: {self.file_path}")
        if self.underlying_error:
            error_parts.append(f"Underlying Error: {str(self.underlying_error)}")
        return " | ".join(error_parts)
