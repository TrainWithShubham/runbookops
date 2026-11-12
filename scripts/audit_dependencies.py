"""Audit locked runtime dependencies with narrow, expiring advisory exceptions."""

import datetime
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def review(report, exceptions, today):
    errors = []
    for dependency in report["dependencies"]:
        for finding in dependency.get("vulns", []):
            exception = next(
                (
                    item
                    for item in exceptions
                    if (item["package"], item["version"], item["advisory"])
                    == (dependency["name"], dependency["version"], finding["id"])
                ),
                None,
            )
            if exception is None:
                errors.append(
                    f"Unreviewed advisory: {dependency['name']} {dependency['version']} {finding['id']}"
                )
            elif datetime.date.fromisoformat(exception["review_by"]) < today:
                errors.append(f"Expired exception: {finding['id']}")
    return errors


def main():
    folder = ROOT / "artifacts/security"
    folder.mkdir(parents=True, exist_ok=True)
    requirements = folder / "runtime-requirements.txt"
    with requirements.open("w") as output:
        subprocess.run(
            [
                "uv",
                "export",
                "--frozen",
                "--no-dev",
                "--extra",
                "aws",
                "--no-emit-project",
                "--format",
                "requirements-txt",
            ],
            cwd=ROOT,
            stdout=output,
            check=True,
        )
    report = folder / "dependencies.json"
    result = subprocess.run(
        [
            "uvx",
            "pip-audit==2.9.0",
            "--disable-pip",
            "--no-deps",
            "-r",
            str(requirements),
            "--format",
            "json",
            "-o",
            str(report),
        ],
        cwd=ROOT,
    )
    if result.returncode not in (0, 1) or not report.exists():
        print("Dependency audit failed to produce a report")
        return 1
    data = json.loads(report.read_text())
    exceptions = json.loads((ROOT / "security/dependency-exceptions.json").read_text())
    errors = review(data, exceptions, datetime.datetime.now(datetime.UTC).date())
    if errors:
        print("\n".join(errors))
        return 1
    count = sum(len(p.get("vulns", [])) for p in data["dependencies"])
    print(
        f"No unreviewed dependency findings. {count} explicitly reviewed upstream advisories remain; see security/dependency-exceptions.json."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
