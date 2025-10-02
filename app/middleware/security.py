"""
Security Middleware

Provides security headers, request sanitization, and rate limiting.
"""

import time
import json
import hashlib
from typing import Dict, Any, Optional, Set
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.core.logging import get_logger
from app.core.config import get_settings

logger = get_logger(__name__)
settings = get_settings()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    
    def __init__(self, app, config: Optional[Dict[str, Any]] = None):
        super().__init__(app)
        self.config = config or {}
        
        # Default security headers
        self.default_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https: blob:; "
                "font-src 'self' data: https:; "
                "connect-src 'self'; "
                "frame-ancestors 'none'"
            )
        }
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Skip security headers for Swagger UI documentation
        if request.url.path.startswith("/docs") or request.url.path.startswith("/redoc"):
            return response
        
        # Add security headers
        for header, value in self.default_headers.items():
            # Allow override from config
            final_value = self.config.get(header, value)
            if final_value:
                response.headers[header] = final_value
        
        return response


class RequestSanitizationMiddleware(BaseHTTPMiddleware):
    """Sanitize incoming requests to prevent XSS and injection attacks."""
    
    def __init__(self, app, config: Optional[Dict[str, Any]] = None):
        super().__init__(app)
        self.config = config or {}
        self.max_request_size = self.config.get("max_request_size", 10 * 1024 * 1024)  # 10MB
        
        # Dangerous patterns to detect
        self.dangerous_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'vbscript:',
            r'onload\s*=',
            r'onerror\s*=',
            r'onclick\s*=',
            r'<iframe[^>]*>',
            r'<object[^>]*>',
            r'<embed[^>]*>',
            r'<link[^>]*>',
            r'<meta[^>]*>',
            r'eval\s*\(',
            r'setTimeout\s*\(',
            r'setInterval\s*\(',
        ]
        
        # SQL injection patterns
        self.sql_patterns = [
            r'union\s+select',
            r'drop\s+table',
            r'delete\s+from',
            r'insert\s+into',
            r'update\s+.*\s+set',
            r'exec\s*\(',
            r'sp_executesql',
            r'xp_cmdshell',
        ]
    
    async def dispatch(self, request: Request, call_next):
        # Check request size
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_request_size:
            logger.warning(f"Request too large: {content_length} bytes from {request.client.host}")
            return JSONResponse(
                status_code=413,
                content={"detail": "Request entity too large"}
            )
        
        # Sanitize request if it has a body
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    # Check for dangerous content
                    body_str = body.decode('utf-8', errors='ignore')
                    
                    if self._contains_dangerous_content(body_str):
                        logger.warning(f"Dangerous content detected from {request.client.host}")
                        return JSONResponse(
                            status_code=400,
                            content={"detail": "Invalid request content"}
                        )
                    
                    # Recreate request with sanitized body
                    sanitized_body = self._sanitize_content(body_str)
                    request._body = sanitized_body.encode('utf-8')
            
            except Exception as e:
                logger.error(f"Error sanitizing request: {str(e)}")
                return JSONResponse(
                    status_code=400,
                    content={"detail": "Invalid request format"}
                )
        
        return await call_next(request)
    
    def _contains_dangerous_content(self, content: str) -> bool:
        """Check if content contains dangerous patterns."""
        import re
        
        content_lower = content.lower()
        
        # Check for XSS patterns
        for pattern in self.dangerous_patterns:
            if re.search(pattern, content_lower, re.IGNORECASE):
                return True
        
        # Check for SQL injection patterns
        for pattern in self.sql_patterns:
            if re.search(pattern, content_lower, re.IGNORECASE):
                return True
        
        return False
    
    def _sanitize_content(self, content: str) -> str:
        """Sanitize content by removing dangerous elements."""
        import re
        
        # Remove script tags and their content
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove dangerous attributes
        dangerous_attrs = ['onload', 'onerror', 'onclick', 'onmouseover', 'onfocus', 'onblur']
        for attr in dangerous_attrs:
            content = re.sub(f'{attr}\\s*=\\s*["\'][^"\']*["\']', '', content, flags=re.IGNORECASE)
        
        # Remove javascript: and vbscript: protocols
        content = re.sub(r'javascript:', '', content, flags=re.IGNORECASE)
        content = re.sub(r'vbscript:', '', content, flags=re.IGNORECASE)
        
        return content


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with in-memory storage."""
    
    def __init__(self, app, config: Optional[Dict[str, Any]] = None):
        super().__init__(app)
        self.config = config or {}
        
        # Rate limiting configuration
        self.requests_per_minute = self.config.get("requests_per_minute", 60)
        self.requests_per_hour = self.config.get("requests_per_hour", 1000)
        self.burst_limit = self.config.get("burst_limit", 10)
        
        # In-memory storage for rate limiting
        self.request_counts: Dict[str, Dict[str, Any]] = {}
        self.cleanup_interval = 300  # 5 minutes
        self.last_cleanup = time.time()
        
        # Exempt paths from rate limiting
        self.exempt_paths: Set[str] = set(self.config.get("exempt_paths", [
            "/health/health",
            "/health/liveness", 
            "/health/readiness"
        ]))
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for exempt paths
        if request.url.path in self.exempt_paths:
            return await call_next(request)
        
        # Get client identifier
        client_id = self._get_client_id(request)
        
        # Check rate limits
        if self._is_rate_limited(client_id):
            logger.warning(f"Rate limit exceeded for client {client_id}")
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": 60
                },
                headers={"Retry-After": "60"}
            )
        
        # Record request
        self._record_request(client_id)
        
        # Cleanup old entries periodically
        self._cleanup_old_entries()
        
        return await call_next(request)
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting."""
        # Try to get real IP from headers (for reverse proxy setups)
        real_ip = (
            request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or
            request.headers.get("X-Real-IP", "") or
            request.client.host if request.client else "unknown"
        )
        
        # Include user agent for additional uniqueness
        user_agent = request.headers.get("User-Agent", "")
        
        # Create hash for privacy
        identifier = f"{real_ip}:{user_agent}"
        return hashlib.md5(identifier.encode()).hexdigest()
    
    def _is_rate_limited(self, client_id: str) -> bool:
        """Check if client has exceeded rate limits."""
        now = time.time()
        
        if client_id not in self.request_counts:
            return False
        
        client_data = self.request_counts[client_id]
        
        # Check burst limit (last 10 requests in 1 minute)
        recent_requests = [
            req_time for req_time in client_data.get("requests", [])
            if now - req_time < 60
        ]
        
        if len(recent_requests) >= self.burst_limit:
            return True
        
        # Check per-minute limit
        minute_requests = [
            req_time for req_time in client_data.get("requests", [])
            if now - req_time < 60
        ]
        
        if len(minute_requests) >= self.requests_per_minute:
            return True
        
        # Check per-hour limit
        hour_requests = [
            req_time for req_time in client_data.get("requests", [])
            if now - req_time < 3600
        ]
        
        if len(hour_requests) >= self.requests_per_hour:
            return True
        
        return False
    
    def _record_request(self, client_id: str):
        """Record a request for rate limiting."""
        now = time.time()
        
        if client_id not in self.request_counts:
            self.request_counts[client_id] = {"requests": []}
        
        self.request_counts[client_id]["requests"].append(now)
        
        # Keep only recent requests (last hour)
        self.request_counts[client_id]["requests"] = [
            req_time for req_time in self.request_counts[client_id]["requests"]
            if now - req_time < 3600
        ]
    
    def _cleanup_old_entries(self):
        """Clean up old rate limiting entries."""
        now = time.time()
        
        if now - self.last_cleanup < self.cleanup_interval:
            return
        
        # Remove clients with no recent requests
        clients_to_remove = []
        for client_id, client_data in self.request_counts.items():
            recent_requests = [
                req_time for req_time in client_data.get("requests", [])
                if now - req_time < 3600
            ]
            
            if not recent_requests:
                clients_to_remove.append(client_id)
            else:
                # Update with only recent requests
                client_data["requests"] = recent_requests
        
        for client_id in clients_to_remove:
            del self.request_counts[client_id]
        
        self.last_cleanup = now
        
        if clients_to_remove:
            logger.info(f"Cleaned up {len(clients_to_remove)} old rate limiting entries")


def get_security_middleware_config() -> Dict[str, Any]:
    """Get security middleware configuration from settings."""
    return {
        "security_headers": {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains" if settings.environment == "production" else None,
        },
        "sanitization": {
            "max_request_size": 10 * 1024 * 1024,  # 10MB
        },
        "rate_limiting": {
            "requests_per_minute": 60,
            "requests_per_hour": 1000,
            "burst_limit": 10,
            "exempt_paths": ["/health/health", "/health/liveness", "/health/readiness"]
        }
    }