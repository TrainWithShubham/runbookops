"""Loopback-only browser bridge. IAM signs cloud calls; demo JWTs retain role checks."""

import asyncio
import contextvars
import json
import re
import threading
import uuid
from contextlib import asynccontextmanager

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from .auth import Auth
from .bridge import allowed_request
from .budget import RunBudget
from .models import Model
from .security import Denied
from .ui import install_shell


class RuntimeClient:
    def __init__(self, arn, qualifier, auth):
        match = re.fullmatch(r"arn:aws:bedrock-agentcore:([a-z0-9-]+):\d{12}:runtime/[A-Za-z0-9_-]+", arn)
        if not match or not re.fullmatch(r"[A-Za-z0-9_]{1,100}", qualifier):
            raise ValueError("Provide a valid AgentCore runtime ARN and endpoint qualifier")
        self.arn, self.qualifier, self.auth = arn, qualifier, auth
        self.identity = contextvars.ContextVar("runtime_identity")
        self.read_sessions = {}
        self.request_lock = threading.Lock()
        self.client = boto3.Session(region_name=match[1]).client(
            "bedrock-agentcore",
            config=Config(connect_timeout=10, read_timeout=180, retries={"total_max_attempts": 1}),
        )
        self.client.meta.events.register_first(
            "before-sign.bedrock-agentcore.InvokeAgentRuntime", self._header
        )

    def _header(self, request, **kwargs):
        request.headers["X-RunbookOps-Token"] = self.identity.get()

    def open(self, payload, actor):
        marker = self.identity.set(self.auth.issue(actor.user, scopes=actor.scopes))
        try:
            response = self.client.invoke_agent_runtime(
                agentRuntimeArn=self.arn,
                qualifier=self.qualifier,
                runtimeSessionId=(
                    self.read_sessions.setdefault(
                        (actor.user, tuple(sorted(actor.scopes))), str(uuid.uuid4())
                    )
                    if payload["operation"] == "request"
                    and (payload.get("method") == "GET" or payload.get("path") == "/knowledge/search")
                    else str(uuid.uuid4())
                ),
                contentType="application/json",
                accept="text/event-stream" if payload["operation"] == "stream" else "application/json",
                payload=json.dumps(payload).encode(),
            )
            return response["response"]
        finally:
            self.identity.reset(marker)

    def request(self, payload, actor):
        # Serialize inspector calls during session startup; retain the role-scoped RAG cache.
        with self.request_lock:
            body = self.open(payload, actor)
            try:
                return json.loads(body.read())
            finally:
                body.close()

    def close(self):
        self.client.close()


def create_presenter_app(settings, arn, qualifier="presenter"):
    auth = Auth(settings)
    if auth.external:
        raise ValueError("Presenter mode requires the local demo signing key configured in Terraform")
    budget = RunBudget(settings.data / "presenter-usage.sqlite", arn)
    runtime = RuntimeClient(arn, qualifier, auth)
    busy = asyncio.Lock()

    @asynccontextmanager
    async def lifespan(app):
        yield
        runtime.close()

    app = FastAPI(title="RunbookOps presenter", lifespan=lifespan)
    app.state.auth, app.state.runtime = auth, runtime
    install_shell(app, settings, auth, Model(settings), backend="Amazon Bedrock AgentCore")

    @app.middleware("http")
    async def local_only(request, call_next):
        origin = request.headers.get("origin")
        if (
            request.client.host not in ("127.0.0.1", "::1")
            or request.url.hostname not in ("localhost", "127.0.0.1", "::1")
            or (origin and origin != str(request.base_url).rstrip("/"))
        ):
            return JSONResponse({"detail": "Presenter access is restricted to this computer"}, 403)
        return await call_next(request)

    @app.get("/health")
    def health():
        return {"status": "Healthy", "backend": "agentcore", "cloud_checked": False}

    @app.api_route("/{path:path}", methods=["GET", "POST"])
    async def proxy(path: str, request: Request):
        streaming = request.method == "POST" and path == "investigations/stream"
        if not streaming and not allowed_request(request.method, "/" + path):
            raise HTTPException(404, "Unknown application route")
        token = request.headers.get("authorization", "")
        if not token.startswith("Bearer "):
            raise HTTPException(401, "Bearer access token required")
        try:
            actor = auth.verify(token[7:])
        except Denied:
            raise HTTPException(401, "Invalid or expired access token") from None
        try:
            data = await request.json() if request.method == "POST" else None
        except ValueError:
            raise HTTPException(422, "Request body must be valid JSON") from None
        if data is not None and not isinstance(data, dict):
            raise HTTPException(422, "Request body must be a JSON object")
        if streaming:
            from .ui import Investigation

            try:
                question = Investigation.model_validate(data).question
            except ValueError:
                raise HTTPException(422, "Provide a question between 1 and 1200 characters") from None
            if busy.locked():
                raise HTTPException(429, "An investigation is already running; wait for it to finish")
            await busy.acquire()
            try:
                budget.admit()
                body = await asyncio.to_thread(
                    runtime.open, {"operation": "stream", "question": question}, actor
                )
            except HTTPException:
                busy.release()
                raise
            except (BotoCoreError, ClientError):
                busy.release()
                raise HTTPException(
                    502, "AgentCore connection failed; check AWS credentials, region, and deployment"
                ) from None

            async def lines():
                try:
                    iterator = body.iter_lines(chunk_size=64)
                    while True:
                        line = await asyncio.to_thread(next, iterator, None)
                        if line is None:
                            break
                        if line:
                            yield line.removeprefix(b"data: ") + b"\n"
                except (BotoCoreError, ClientError, OSError):
                    yield (
                        json.dumps(
                            {
                                "type": "error",
                                "data": {
                                    "message": "AgentCore stream interrupted; inspect saved work before retrying"
                                },
                            }
                        ).encode()
                        + b"\n"
                    )
                finally:
                    body.close()
                    busy.release()

            return StreamingResponse(
                lines(), media_type="application/x-ndjson", headers={"Cache-Control": "no-store"}
            )
        payload = {"operation": "request", "method": request.method, "path": "/" + path, "body": data}
        starting = request.method == "POST" and path == "investigations"
        if starting:
            if busy.locked():
                raise HTTPException(429, "An investigation is already running; wait for it to finish")
            await busy.acquire()
        try:
            if starting:
                budget.admit()
            response = await asyncio.to_thread(runtime.request, payload, actor)
        except (BotoCoreError, ClientError):
            raise HTTPException(
                502, "AgentCore request failed; inspect AWS access and runtime logs"
            ) from None
        finally:
            if starting:
                busy.release()
        return JSONResponse(
            response["body"], status_code=response["status_code"], headers={"Cache-Control": "no-store"}
        )

    return app
