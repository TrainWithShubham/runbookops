"""Verify the Compose UI/API and approval recovery across a real container restart."""

import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:8006"


def request(method, path, token="", payload=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers=headers,
        method=method,
    )
    try:
        response = urllib.request.urlopen(req, timeout=30)
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())
    with response:
        return response.status, json.loads(response.read())


def token(user):
    return subprocess.check_output(
        ["docker", "compose", "exec", "-T", "app", "runbookops", "--as", user, "token"], cwd=ROOT, text=True
    ).strip()


def main():
    viewer, approver = token("bagha"), token("jethalal")
    assert request("GET", "/me")[0] == 401
    status, state = request(
        "POST", "/investigations", viewer, {"question": "Check checkout and prepare a fix for approval."}
    )
    assert status == 200 and state["health"]["http_status"] == 503
    proposal = state["proposal"]
    path = f"/proposals/{proposal['id']}/decision"
    decision = {"expected_hash": proposal["hash"], "approve": True}
    assert request("POST", path, viewer, decision)[0] == 403
    subprocess.run(["docker", "compose", "restart", "app"], cwd=ROOT, check=True)
    for _ in range(40):
        try:
            if request("GET", "/health")[0] == 200:
                break
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(0.5)
    status, recovered = request("POST", path, approver, decision)
    assert status == 200 and recovered["health"]["http_status"] == 200
    assert request("POST", path, approver, decision)[0] in (403, 409)
    status, discovered = request("GET", "/harness/mcp", viewer)
    assert status == 200 and len(discovered["tools"]) == 5
    report = {
        "backend": "docker-compose-offline",
        "viewer_denied": True,
        "restart_resume_verified": True,
        "duplicate_approval_denied": True,
        "recovered_http_status": 200,
        "mcp_tools": [t["name"] for t in discovered["tools"]],
    }
    target = ROOT / "artifacts/container-smoke.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + "\n")
    print(
        "Container smoke passed: denied viewer, restart/resume, approved HTTP 200, duplicate denied. Tokens not displayed."
    )


if __name__ == "__main__":
    main()
