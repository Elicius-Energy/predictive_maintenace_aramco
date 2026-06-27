import time
import uuid
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        
        request_id = getattr(request.state, "request_id", "unknown")
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # Don't log health checks as aggressively to avoid noise
            if request.url.path == "/api/health":
                logger.debug(f"{request.method} {request.url.path} - {response.status_code} ({process_time:.3f}s)")
            else:
                logger.info(f"[{request_id}] {request.method} {request.url.path} - {response.status_code} ({process_time:.3f}s)")
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(f"[{request_id}] {request.method} {request.url.path} - 500 INTERNAL_SERVER_ERROR ({process_time:.3f}s) - {str(e)}")
            raise
