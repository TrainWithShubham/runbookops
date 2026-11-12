"""Presenter boundaries and a complete local-to-runtime HTTP contract, without AWS calls."""

import dataclasses
import io
import json
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

pytest.importorskip("boto3")

from botocore.exceptions import EndpointConnectionError

from runbookops import cli, presenter
from runbookops.api import create_app
from runbookops.auth import Auth
from runbookops.bridge import allowed_request
from runbookops.budget import RunBudget
from runbookops.security import InvalidChange, principal

ARN = "arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/runbookops_presenter-example"


def test_bridge_routes_reject_arbitrary_paths_and_methods():
    for method, path in (
        ("GET", "/harness/mcp"),
        ("GET", "/knowledge/checkout-runbook"),
        ("POST", "/incidents/gada-abc/resume"),
        ("POST", "/proposals/proposal:gada-0123456789ab:0123456789/decision"),
    ):
        assert allowed_request(method, path)
    for method, path in (
        ("DELETE", "/knowledge"),
        ("POST", "/invocations"),
        ("GET", "https://evil.example/me"),
        ("GET", "/knowledge/../me"),
        ("GET", "/ui/session"),
        ("GET", "/me?admin=true"),
    ):
        assert not allowed_request(method, path)


def test_runtime_envelopes_keep_route_validation_and_role_checks(settings):
    app = create_app(settings)
    auth = app.state.auth
    with TestClient(app) as cloud:
        assert cloud.post("/invocations", json={"operation": "health"}).json() == {
            "status": "Healthy",
            "mode": "offline",
            "durable_state": False,
        }
        headers = {"Authorization": "Bearer " + auth.issue("bagha")}
        result = cloud.post(
            "/invocations", headers=headers, json={"operation": "request", "path": "/me"}
        ).json()
        assert result["status_code"] == 200 and result["body"]["role"] == "viewer"
        assert (
            cloud.post(
                "/invocations", headers=headers, json={"operation": "request", "path": "/invocations"}
            ).status_code
            == 422
        )
        rows = cloud.post(
            "/invocations",
            headers=headers,
            json={"operation": "stream", "question": "Check checkout and prepare the documented correction."},
        )
        events = [json.loads(line.removeprefix("data: ")) for line in rows.text.splitlines() if line]
        assert events[0]["type"] == "connected"
        assert events[-1]["type"] == "complete"
        assert events[-1]["data"]["waiting_for_approval"]
        assert any(row["type"] == "event" and row["data"]["kind"] == "tool" for row in events)


@pytest.fixture
def bridge(settings, monkeypatch):
    cloud = TestClient(create_app(settings))

    class Stream(io.BytesIO):
        def iter_lines(self, **kwargs):
            return iter(self.getvalue().splitlines())

    class FakeRuntime:
        error = False
        broken_stream = False
        closed = False

        def __init__(self, arn, qualifier, auth):
            self.auth = auth

        def open(self, payload, actor):
            if self.error:
                raise EndpointConnectionError(endpoint_url="https://runtime.invalid")
            response = cloud.post(
                "/invocations",
                json=payload,
                headers={"Authorization": "Bearer " + self.auth.issue(actor.user, scopes=actor.scopes)},
            )
            if self.broken_stream:
                body = Mock()
                body.iter_lines.side_effect = OSError("private transport diagnostic")
                return body
            return Stream(response.content)

        def request(self, payload, actor):
            body = self.open(payload, actor)
            return json.loads(body.read())

        def close(self):
            self.closed = True

    monkeypatch.setattr(presenter, "RuntimeClient", FakeRuntime)
    app = presenter.create_presenter_app(dataclasses.replace(settings, ui_demo_auth=True), ARN)
    with cloud, TestClient(app, base_url="http://127.0.0.1", client=("127.0.0.1", 50000)) as client:
        token = app.state.auth.issue("bagha")
        client.headers["Authorization"] = "Bearer " + token
        yield app, client
    assert app.state.runtime.closed


def test_presenter_runs_complete_cloud_contract_and_all_inspectors(bridge):
    app, client = bridge
    assert client.get("/").status_code == 200
    assert client.get("/health").json()["backend"] == "agentcore"
    assert client.get("/ui/config").json()["demo_auth"]
    for path in ("/me", "/harness", "/harness/mcp", "/knowledge", "/knowledge/architecture"):
        assert client.get(path).status_code == 200
    assert client.post("/knowledge/search", json={"question": "checkout payment runbook"}).json()["results"]
    rows = client.post(
        "/investigations/stream", json={"question": "Check checkout and prepare a fix for approval."}
    )
    state = json.loads(rows.text.splitlines()[-1])["data"]
    proposal = state["proposal"]
    path = f"/proposals/{proposal['id']}/decision"
    decision = {"expected_hash": proposal["hash"], "approve": True}
    assert client.post(path, json=decision).status_code == 403
    client.headers["Authorization"] = "Bearer " + app.state.auth.issue("jethalal")
    assert client.post(path, json=decision).json()["health"]["http_status"] == 200
    assert client.get(f"/incidents/{state['incident_id']}/trace").json()["events"]
    assert client.get(f"/incidents/{state['incident_id']}").json()["health"]["http_status"] == 200
    assert client.post("/investigations", json={"question": "Check checkout."}).json()["incident_id"]


def test_presenter_rejects_bad_auth_origin_routes_and_payloads(bridge):
    app, client = bridge
    assert client.get("/invocations").status_code == 404
    assert client.get("/me", headers={"Origin": "https://evil.example"}).status_code == 403
    client.headers.pop("Authorization")
    assert client.get("/me").status_code == 401
    client.headers["Authorization"] = "Bearer broken"
    assert client.get("/me").status_code == 401
    client.headers["Authorization"] = "Bearer " + app.state.auth.issue("bagha")
    assert client.post("/investigations/stream", content="{").status_code == 422
    assert client.post("/knowledge/search", json=[]).status_code == 422
    for body in ({}, {"question": ""}, {"question": "valid", "extra": True}):
        assert client.post("/investigations/stream", json=body).status_code == 422
    with TestClient(app, base_url="http://evil.example", client=("127.0.0.1", 4)) as wrong_host:
        assert wrong_host.get("/").status_code == 403
    with TestClient(app, base_url="http://127.0.0.1", client=("10.0.0.1", 4)) as remote:
        assert remote.get("/").status_code == 403


def test_connection_errors_do_not_fallback_or_leak_diagnostics(bridge):
    app, client = bridge
    app.state.runtime.error = True
    assert client.get("/harness").status_code == 502
    assert client.post("/investigations", json={"question": "Check."}).status_code == 502
    assert client.post("/investigations/stream", json={"question": "Check."}).status_code == 502
    app.state.runtime.error = False
    app.state.runtime.broken_stream = True
    result = client.post("/investigations/stream", json={"question": "Check."})
    assert "stream interrupted" in result.text and "private transport" not in result.text
    app.state.runtime.broken_stream = False
    assert client.post("/investigations/stream", json={"question": "Check."}).status_code == 200


def test_runtime_client_closes_bodies_and_isolates_concurrent_identity(settings, monkeypatch):
    sdk = Mock()
    monkeypatch.setattr(presenter.boto3, "Session", lambda **kw: Mock(client=Mock(return_value=sdk)))
    auth = Auth(settings)
    runtime = presenter.RuntimeClient(ARN, "presenter", auth)

    def respond(**kwargs):
        request = Mock(headers={})
        runtime._header(request)
        actor = auth.verify(request.headers["X-RunbookOps-Token"])
        payload = json.loads(kwargs["payload"])
        assert kwargs["runtimeSessionId"]
        return {"response": io.BytesIO(json.dumps({"user": actor.user, "payload": payload}).encode())}

    sdk.invoke_agent_runtime.side_effect = respond
    with ThreadPoolExecutor(2) as pool:
        results = list(
            pool.map(
                lambda user: runtime.request({"operation": "request"}, principal(user)), ("bagha", "jethalal")
            )
        )
    assert [row["user"] for row in results] == ["bagha", "jethalal"]
    body = runtime.open({"operation": "stream"}, principal("bagha"))
    assert json.loads(body.read())["user"] == "bagha"
    body.close()
    read = {"operation": "request", "method": "GET", "path": "/harness"}
    runtime.request(read, principal("bagha"))
    first_session = sdk.invoke_agent_runtime.call_args.kwargs["runtimeSessionId"]
    runtime.request(
        {"operation": "request", "method": "POST", "path": "/knowledge/search"}, principal("bagha")
    )
    assert sdk.invoke_agent_runtime.call_args.kwargs["runtimeSessionId"] == first_session
    runtime.request(read, principal("jethalal"))
    assert sdk.invoke_agent_runtime.call_args.kwargs["runtimeSessionId"] != first_session
    runtime.close()
    sdk.close.assert_called_once()
    for arn, qualifier in (("invalid", "presenter"), (ARN, "invalid/endpoint")):
        with pytest.raises(ValueError, match="valid AgentCore"):
            presenter.RuntimeClient(arn, qualifier, auth)
    with pytest.raises(ValueError, match="local demo signing"):
        presenter.create_presenter_app(
            dataclasses.replace(settings, oidc_issuer=auth.issuer, oidc_public_key=auth.public), ARN
        )


def test_budget_persists_admission_and_disable_switch(settings, monkeypatch):
    path = settings.data / "limits.sqlite"
    monkeypatch.setenv("RUNBOOKOPS_PRESENTER_DAILY_RUNS", "2")
    RunBudget(path, ARN).admit()
    RunBudget(path, ARN).admit()
    with pytest.raises(HTTPException) as limited:
        RunBudget(path, ARN).admit()
    assert limited.value.status_code == 429
    RunBudget(path, "other-runtime").admit()
    monkeypatch.setenv("RUNBOOKOPS_LIVE_ENABLED", "false")
    with pytest.raises(HTTPException) as disabled:
        RunBudget(path, ARN).admit()
    assert disabled.value.status_code == 503
    monkeypatch.setenv("RUNBOOKOPS_PRESENTER_DAILY_RUNS", "0")
    with pytest.raises(ValueError):
        RunBudget(path, ARN)


def test_presenter_disable_and_quota_release_busy_lock(bridge, monkeypatch):
    _, client = bridge
    monkeypatch.setenv("RUNBOOKOPS_LIVE_ENABLED", "false")
    assert client.post("/investigations/stream", json={"question": "Check."}).status_code == 503
    assert client.post("/investigations", json={"question": "Check."}).status_code == 503
    assert client.get("/harness").status_code == 200
    monkeypatch.setenv("RUNBOOKOPS_LIVE_ENABLED", "true")
    assert client.post("/investigations/stream", json={"question": "Check."}).status_code == 200


def test_presenter_cli_binds_only_loopback(settings, monkeypatch):
    app = Mock()
    monkeypatch.setattr(presenter, "create_presenter_app", lambda *args: app)
    monkeypatch.setattr(cli.Settings, "load", lambda *a, **kw: settings)
    import uvicorn

    run = Mock()
    monkeypatch.setattr(uvicorn, "run", run)
    monkeypatch.setattr("sys.argv", ["runbookops", "present", "--runtime-arn", ARN])
    assert cli.main() == 0
    run.assert_called_once_with(app, host="127.0.0.1", port=8005)


async def test_concurrent_investigations_are_rejected_without_starting_more_work(bridge):
    from starlette.requests import Request

    app, _ = bridge
    endpoint = next(route.endpoint for route in app.routes if route.path == "/{path:path}")
    token = app.state.auth.issue("bagha")

    def request(path):
        async def receive():
            return {"type": "http.request", "body": b'{"question":"Check checkout."}', "more_body": False}

        return Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/" + path,
                "headers": [(b"authorization", ("Bearer " + token).encode())],
                "query_string": b"",
            },
            receive,
        )

    response = await endpoint("investigations/stream", request("investigations/stream"))
    try:
        for path in ("investigations", "investigations/stream"):
            with pytest.raises(HTTPException) as limited:
                await endpoint(path, request(path))
            assert limited.value.status_code == 429
    finally:
        async for _ in response.body_iterator:
            pass


async def test_cloudwatch_connector_is_optional_readonly_and_redacted(settings, monkeypatch):
    import boto3
    from fastmcp import Client

    from runbookops.cloudwatch import read_logs
    from runbookops.mcp_server import create_server
    from runbookops.store import Store
    from runbookops.tools import SCHEMAS, schemas

    assert schemas() == SCHEMAS
    with pytest.raises(InvalidChange, match="sample log group"):
        read_logs()
    monkeypatch.setenv("RUNBOOKOPS_CLOUDWATCH_LOG_GROUP", "/runbookops/presenter-sample")
    monkeypatch.setenv("AWS_REGION", "us-west-2")
    from types import SimpleNamespace

    from botocore.stub import Stubber

    from runbookops import cloudwatch

    logs = boto3.client(
        "logs", region_name="us-west-2", aws_access_key_id="testing", aws_secret_access_key="testing"
    )
    stub = Stubber(logs)
    stub.add_response(
        "filter_log_events",
        {
            "events": [{"timestamp": 123, "message": "synthetic API_KEY=sk-test-only-secret"}],
            "nextToken": "more-results",
        },
        {
            "logGroupName": "/runbookops/presenter-sample",
            "startTime": 100000,
            "endTime": 1000000,
            "limit": 20,
        },
    )
    stub.activate()
    monkeypatch.setattr(cloudwatch.time, "time", lambda: 1000)
    monkeypatch.setattr(boto3, "Session", lambda **kwargs: SimpleNamespace(client=lambda *a, **kw: logs))
    actor = principal("bagha")
    store = Store(settings)
    incident = store.create_incident(actor)["id"]
    store.close()
    server, store = create_server(settings, actor)
    try:
        async with Client(server) as client:
            discovered = {tool.name for tool in await client.list_tools()}
            assert "read_cloudwatch_logs" in discovered
            response = await client.call_tool("read_cloudwatch_logs", {"incident_id": incident})
            result = response.data
            assert result["source"] == "aws-cloudwatch" and result["demo_only"]
            assert "sk-test-only-secret" not in json.dumps(result)
            assert result["truncated"]
            stub.assert_no_pending_responses()
    finally:
        store.close()
