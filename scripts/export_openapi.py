from __future__ import annotations

import json
from pathlib import Path

from api_bridge.config import Settings
from api_bridge.main import create_app


def main() -> None:
    app = create_app(settings=Settings(bridge_token="openapi-placeholder"))
    path = Path("docs/openapi.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
