"""可选：内网访问令牌校验（仅 /api/*）。"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from .deploy_config import api_token


class WorkbenchAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        token = api_token()
        if not token:
            return await call_next(request)
        path = request.url.path
        if path in ("/", "/api/health") or path.startswith("/static/"):
            return await call_next(request)
        if not path.startswith("/api/"):
            return await call_next(request)
        provided = (request.headers.get("x-workbench-token") or request.query_params.get("token") or "").strip()
        if provided != token:
            return JSONResponse(status_code=401, content={"detail": "未授权，请配置 WORKBENCH_API_TOKEN"})
        return await call_next(request)
