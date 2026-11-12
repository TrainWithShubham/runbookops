"""Check local Markdown links in application documentation."""

import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]


def main():
    errors = []
    files = [
        p
        for p in ROOT.rglob("*.md")
        if not any(
            part.startswith(".") or part in ("artifacts", "node_modules")
            for part in p.relative_to(ROOT).parts
        )
    ]
    for path in files:
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text()):
            target = target.strip("<>").split("#")[0]
            if not target or "://" in target or target.startswith(("mailto:", "plugin:")):
                continue
            resolved = path.parent / unquote(target)
            if not resolved.exists():
                errors.append(str(path.relative_to(ROOT)) + ": " + target)
    if errors:
        print("\n".join(errors))
        return 1
    print(f"Checked local links in {len(files)} Markdown files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
