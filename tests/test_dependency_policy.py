"""An unrelated version or an expired exception cannot bypass the dependency gate."""

import datetime
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "audit", Path(__file__).resolve().parents[1] / "scripts/audit_dependencies.py"
)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_dependency_exceptions_are_exact_and_expiring():
    report = {"dependencies": [{"name": "example", "version": "1.0", "vulns": [{"id": "ADVISORY-1"}]}]}
    today = datetime.date(2026, 11, 12)
    item = {"package": "example", "version": "1.0", "advisory": "ADVISORY-1", "review_by": "2026-11-13"}
    assert audit.review(report, [item], today) == []
    assert "Unreviewed" in audit.review(report, [{**item, "version": "2.0"}], today)[0]
    assert "Expired" in audit.review(report, [{**item, "review_by": "2026-11-11"}], today)[0]
    assert audit.review({"dependencies": []}, [], today) == []
