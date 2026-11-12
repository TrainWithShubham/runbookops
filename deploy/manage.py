"""Prepare, publish, and verify a Terraform-managed presenter deployment."""

import argparse
import base64
import datetime
import json
import os
import re
import subprocess
import tempfile
import uuid
from contextlib import closing
from pathlib import Path

import boto3
from botocore.config import Config

from runbookops.auth import Auth
from runbookops.cli import DEFAULT_QUESTION
from runbookops.config import Settings
from runbookops.presenter import RuntimeClient
from runbookops.security import principal

ROOT = Path(__file__).resolve().parents[1]
TF = ROOT / "infra/terraform/presenter"


def run(*args, **kwargs):
    return subprocess.run(list(args), cwd=ROOT, check=True, text=True, **kwargs)


def session(region):
    return boto3.Session(region_name=region)


def configure(region, github_repository=None):
    sdk = session(region)
    config = Config(connect_timeout=10, read_timeout=30, retries={"total_max_attempts": 3})
    account = sdk.client("sts", config=config).get_caller_identity()["Account"]
    supplied_public = os.getenv("RUNBOOKOPS_PRESENTER_PUBLIC_KEY", "")
    auth = None if supplied_public else Auth(Settings(root=ROOT))
    if auth is not None and auth.external:
        raise ValueError("Configure from a local presenter checkout, without an external OIDC issuer")
    public_key = supplied_public or auth.public
    target = TF / "terraform.tfvars.json"
    previous = json.loads(target.read_text()) if target.exists() else {}
    if supplied_public:
        deployed = outputs()
        for key in ("cloudwatch_log_group", "max_calls", "model_id"):
            if key in deployed:
                previous[key] = deployed[key]["value"]
    model_id = previous.get("model_id", "us.amazon.nova-lite-v1:0")
    profile = sdk.client("bedrock", config=config).get_inference_profile(inferenceProfileIdentifier=model_id)
    values = {
        **previous,
        "region": region,
        "model_id": model_id,
        "public_key": public_key,
        "model_arns": [profile["inferenceProfileArn"], *[m["modelArn"] for m in profile["models"]]],
    }
    target.write_text(json.dumps(values, indent=2) + "\n")
    target.chmod(0o600)
    if not supplied_public:
        providers = sdk.client("iam", config=config).list_open_id_connect_providers()[
            "OpenIDConnectProviderList"
        ]
        existing = next(
            (p["Arn"] for p in providers if p["Arn"].endswith("/token.actions.githubusercontent.com")), ""
        )
        bootstrap = ROOT / "infra/terraform/bootstrap/terraform.tfvars.json"
        previous_bootstrap = json.loads(bootstrap.read_text()) if bootstrap.exists() else {}
        selected_repository = (
            github_repository
            if github_repository is not None
            else previous_bootstrap.get("github_repository", "")
        )
        bootstrap.write_text(
            json.dumps(
                {
                    "region": region,
                    "github_oidc_provider_arn": existing,
                    "github_repository": selected_repository,
                },
                indent=2,
            )
            + "\n"
        )
        bootstrap.chmod(0o600)
    public = ROOT / ".state/presenter-public.pem"
    public.parent.mkdir(exist_ok=True)
    public.write_text(public_key)
    print(
        f"Prepared ignored Terraform configuration for account {account}, region {region}. Public key: {public.relative_to(ROOT)}"
    )


def outputs():
    return json.loads(run("terraform", f"-chdir={TF}", "output", "-json", capture_output=True).stdout)


def publish(region, tag):
    if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}", tag):
        raise ValueError("Use a valid immutable image tag")
    repository = outputs().get("repository_url", {}).get("value", "")
    if not repository:
        raise ValueError("Apply the Terraform foundation before publishing an image")
    if not repository.endswith("/runbookops-presenter") or f".ecr.{region}." not in repository:
        raise ValueError("Terraform output does not identify this region's presenter repository")
    sdk = session(region).client(
        "ecr", config=Config(connect_timeout=10, read_timeout=60, retries={"total_max_attempts": 3})
    )
    try:
        existing = sdk.describe_images(repositoryName="runbookops-presenter", imageIds=[{"imageTag": tag}])[
            "imageDetails"
        ][0]
    except sdk.exceptions.ImageNotFoundException:
        existing = None
    if existing is not None:
        path = TF / "terraform.tfvars.json"
        data = json.loads(path.read_text())
        data["image_uri"] = repository + "@" + existing["imageDigest"]
        path.write_text(json.dumps(data, indent=2) + "\n")
        sdk.close()
        print("Reusing the existing immutable image for tag " + tag)
        return
    token = sdk.get_authorization_token()["authorizationData"][0]
    username, password = base64.b64decode(token["authorizationToken"]).decode().split(":", 1)
    image = repository + ":" + tag
    with tempfile.TemporaryDirectory(prefix="runbookops-docker-") as folder:
        environment = {**os.environ, "DOCKER_CONFIG": folder}
        run(
            "docker",
            "login",
            "--username",
            username,
            "--password-stdin",
            token["proxyEndpoint"],
            input=password,
            env=environment,
        )
        run(
            "docker",
            "buildx",
            "build",
            "--platform",
            "linux/arm64",
            "--target",
            "agentcore",
            "--provenance=false",
            "--load",
            "-t",
            image,
            ".",
        )
        run("docker", "push", image, env=environment)
    digest = sdk.describe_images(repositoryName="runbookops-presenter", imageIds=[{"imageTag": tag}])[
        "imageDetails"
    ][0]["imageDigest"]
    path = TF / "terraform.tfvars.json"
    data = json.loads(path.read_text())
    data["image_uri"] = repository + "@" + digest
    path.write_text(json.dumps(data, indent=2) + "\n")
    print("Pinned runtime image to " + data["image_uri"])
    sdk.close()


def smoke(arn=None):
    arn = arn or outputs()["runtime_arn"]["value"]
    settings = Settings(root=ROOT)
    runtime = RuntimeClient(arn, "presenter", Auth(settings))
    stream = None
    try:
        stream = runtime.open({"operation": "stream", "question": DEFAULT_QUESTION}, principal("bagha"))
        rows = [json.loads(line.removeprefix(b"data: ")) for line in stream.iter_lines() if line]
        if not rows or rows[-1].get("type") != "complete":
            raise RuntimeError("Cloud investigation did not complete; inspect runtime logs")
        state = rows[-1]["data"]
        proposal = state.get("proposal")
        if not proposal:
            raise RuntimeError("Cloud model did not prepare a valid proposal")
        path = f"/proposals/{proposal['id']}/decision"
        data = {"expected_hash": proposal["hash"], "approve": True}
        payload = {"operation": "request", "method": "POST", "path": path, "body": data}
        denied = runtime.request(payload, principal("bagha"))
        if denied["status_code"] != 403:
            raise RuntimeError("Viewer approval boundary failed")
        approved = runtime.request(payload, principal("jethalal"))
        if approved["status_code"] != 200 or approved["body"]["health"]["http_status"] != 200:
            raise RuntimeError("Approved cloud recovery did not return HTTP 200")
        discovered = runtime.request(
            {"operation": "request", "method": "GET", "path": "/harness/mcp"}, principal("bagha")
        )
        report = {
            "verified_at": datetime.datetime.now(datetime.UTC).isoformat(),
            "backend": "agentcore",
            "denied_viewer": True,
            "verified_http_status": 200,
            "separate_runtime_sessions": True,
            "stream_event_types": sorted({row["type"] for row in rows}),
            "mcp_tools": [tool["name"] for tool in discovered["body"]["tools"]],
            "incident_id": state["incident_id"],
            "model_calls": state["model_calls"],
        }
        target = ROOT / "artifacts/presenter-cloud-smoke.json"
        target.parent.mkdir(exist_ok=True)
        target.write_text(json.dumps(report, indent=2) + "\n")
        print(
            "AgentCore smoke passed: real events, viewer denied, approver recovered HTTP 200. "
            + str(target.relative_to(ROOT))
        )
    finally:
        if stream is not None:
            stream.close()
        runtime.close()


def probe(arn=None):
    arn = arn or outputs()["runtime_arn"]["value"]
    region = arn.split(":")[3]
    with closing(
        session(region).client(
            "bedrock-agentcore",
            config=Config(connect_timeout=10, read_timeout=180, retries={"total_max_attempts": 1}),
        )
    ) as client:
        response = client.invoke_agent_runtime(
            agentRuntimeArn=arn,
            qualifier="presenter",
            runtimeSessionId=uuid.uuid4().hex + "-health",
            payload=json.dumps({"operation": "health"}).encode(),
            contentType="application/json",
            accept="application/json",
        )
        with response["response"] as body:
            status = json.loads(body.read())
    if status.get("status") != "Healthy" or not status.get("durable_state"):
        raise RuntimeError("Runtime health/durable state probe failed")
    print("IAM-authenticated runtime health and durable configuration verified. No inference requested.")


def logs(region):
    arn = outputs()["runtime_arn"]["value"]
    runtime_id = arn.rsplit("/", 1)[1]
    state_bucket = (
        os.getenv("TF_STATE_BUCKET")
        or json.loads(
            run(
                "terraform", "-chdir=infra/terraform/bootstrap", "output", "-json", capture_output=True
            ).stdout
        )["state_bucket"]["value"]
    )
    folder = ROOT / "infra/terraform/logs"
    (folder / "terraform.tfvars.json").write_text(
        json.dumps({"region": region, "runtime_id": runtime_id}) + "\n"
    )
    run(
        "terraform",
        f"-chdir={folder}",
        "init",
        "-input=false",
        f"-backend-config=bucket={state_bucket}",
        f"-backend-config=region={region}",
    )
    run("terraform", f"-chdir={folder}", "plan", "-input=false", "-out=logs.tfplan")
    run("terraform", f"-chdir={folder}", "apply", "-input=false", "logs.tfplan")


def seed_logs(region):
    values = json.loads((TF / "terraform.tfvars.json").read_text())
    group = values.get("cloudwatch_log_group", "")
    if not group.startswith("/runbookops/"):
        raise ValueError("Enable a project sample log group in Terraform first")
    with closing(
        session(region).client(
            "logs", config=Config(connect_timeout=5, read_timeout=10, retries={"total_max_attempts": 2})
        )
    ) as client:
        stream = "sample-" + datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%S%f")
        client.create_log_stream(logGroupName=group, logStreamName=stream)
        client.put_log_events(
            logGroupName=group,
            logStreamName=stream,
            logEvents=[
                {
                    "timestamp": int(datetime.datetime.now(datetime.UTC).timestamp() * 1000),
                    "message": "SYNTHETIC DEMO: checkout HTTP 503, payment connection refused after deploy-108; no real customer data.",
                }
            ],
        )
    print("Seeded one synthetic CloudWatch event. Agent permissions remain read-only.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", default="us-west-2")
    commands = parser.add_subparsers(dest="command", required=True)
    configuration = commands.add_parser("configure")
    configuration.add_argument(
        "--github-repository",
        help="Explicit owner/repo to trust for CI; omitted leaves CI federation disabled on a new setup",
    )
    commands.add_parser("seed-logs")
    commands.add_parser("logs")
    image = commands.add_parser("publish")
    image.add_argument("--tag", required=True)
    health = commands.add_parser("probe")
    health.add_argument("--runtime-arn")
    verify = commands.add_parser("smoke")
    verify.add_argument("--runtime-arn")
    args = parser.parse_args()
    if args.command == "configure":
        configure(args.region, args.github_repository)
    elif args.command == "publish":
        publish(args.region, args.tag)
    elif args.command == "logs":
        logs(args.region)
    elif args.command == "probe":
        probe(args.runtime_arn)
    elif args.command == "seed-logs":
        seed_logs(args.region)
    else:
        smoke(args.runtime_arn)


if __name__ == "__main__":
    main()
