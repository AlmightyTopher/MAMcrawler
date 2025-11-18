"""
SQLAlchemy ORM model for ApiLog table
Tracks all API requests for monitoring and debugging
"""

from sqlalchemy import Column, Integer, String, Float, TIMESTAMP, Text, JSON, func
from datetime import datetime

from backend.database import Base


class ApiLog(Base):
    """
    ApiLog model representing API request logs

    Attributes:
        id: Primary key
        method: HTTP method (GET, POST, etc.)
        path: Request path
        status_code: Response status code
        response_time_ms: Response time in milliseconds
        user_agent: Client user agent
        ip_address: Client IP address
        request_body: Request body (for POST/PUT)
        response_size: Response size in bytes
        error_message: Error message if request failed
        timestamp: Request timestamp
    """

    __tablename__ = "api_logs"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Request info
    method = Column(String(10), nullable=False, index=True)
    path = Column(String(500), nullable=False, index=True)
    query_params = Column(Text, nullable=True)

    # Response info
    status_code = Column(Integer, nullable=False, index=True)
    response_time_ms = Column(Float, nullable=False)
    response_size = Column(Integer, nullable=True)

    # Client info
    user_agent = Column(String(500), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 max length

    # Body/error tracking
    request_body = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

    # Timestamp
    timestamp = Column(TIMESTAMP, default=func.now(), index=True)

    def __repr__(self) -> str:
        return f"<ApiLog(id={self.id}, {self.method} {self.path} -> {self.status_code})>"
