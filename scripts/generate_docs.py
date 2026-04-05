"""Generate static API docs from the Flask app's OpenAPI spec.

Usage:
    uv run python scripts/generate_docs.py

Outputs:
    docs/api/openapi.json  — raw OpenAPI 3.0 spec
    docs/api/index.html    — Swagger UI static docs
"""

import json
import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import create_app

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "api")

SWAGGER_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>URL Shortener API</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist/swagger-ui.css" />
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist/swagger-ui-bundle.js"></script>
  <script>
    SwaggerUIBundle({
      url: "openapi.json",
      dom_id: "#swagger-ui",
      presets: [
        SwaggerUIBundle.presets.apis,
        SwaggerUIBundle.SwaggerUIStandalonePreset
      ]
    });
  </script>
</body>
</html>
"""


def main():
    # Patch DB so we don't need Postgres running — only the OpenAPI spec is needed
    with patch("app.init_db"), \
         patch("app.db") as mock_db:
        mock_db.create_tables = MagicMock()
        mock_db.is_closed.return_value = True
        app = create_app()

    with app.test_client() as client:
        resp = client.get("/apidocs/openapi.json")
        if resp.status_code != 200:
            print(f"Failed to fetch OpenAPI spec: {resp.status_code}", file=sys.stderr)
            sys.exit(1)
        spec = resp.get_json()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    spec_path = os.path.join(OUTPUT_DIR, "openapi.json")
    with open(spec_path, "w") as f:
        json.dump(spec, f, indent=2)
    print(f"Wrote {spec_path}")

    html_path = os.path.join(OUTPUT_DIR, "index.html")
    with open(html_path, "w") as f:
        f.write(SWAGGER_HTML)
    print(f"Wrote {html_path}")


if __name__ == "__main__":
    main()
