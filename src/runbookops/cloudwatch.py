"""Optional read-only connector for one project-owned sample log group."""

import os
import time
from contextlib import closing

from .security import InvalidChange, redact


def read_logs():
    group = os.getenv("RUNBOOKOPS_CLOUDWATCH_LOG_GROUP", "")
    if not group.startswith("/runbookops/"):
        raise InvalidChange("Configure a project-owned /runbookops/ sample log group first")
    import boto3
    from botocore.config import Config

    with closing(
        boto3.Session(region_name=os.getenv("AWS_REGION", "us-west-2")).client(
            "logs", config=Config(connect_timeout=5, read_timeout=10, retries={"total_max_attempts": 2})
        )
    ) as client:
        end = int(time.time() * 1000)
        result = client.filter_log_events(logGroupName=group, startTime=end - 900000, endTime=end, limit=20)
    return {
        "source": "aws-cloudwatch",
        "demo_only": True,
        "log_group": group,
        "events": [
            {"timestamp": event["timestamp"], "message": redact(event["message"][:2000])}
            for event in result["events"]
        ],
        "truncated": bool(result.get("nextToken")),
    }
