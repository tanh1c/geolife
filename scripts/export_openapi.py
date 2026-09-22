from __future__ import annotations

from pathlib import Path

import yaml

from geolife.api.app import app


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "openapi.yaml"


def main() -> None:
    schema = app.openapi()
    with TARGET.open("w", encoding="utf-8", newline="\n") as output:
        output.write(yaml.safe_dump(schema, sort_keys=False, allow_unicode=True))
    print(f"Wrote {TARGET}")


if __name__ == "__main__":
    main()
