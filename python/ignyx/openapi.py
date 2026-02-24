"""
OpenAPI schema generation and Swagger UI / ReDoc serving.
Auto-generates OpenAPI 3.0 schema from registered routes.
"""

import json
from typing import Any, Optional


SWAGGER_UI_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>{title} - Swagger UI</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-standalone-preset.js"></script>
    <script>
        SwaggerUIBundle({{
            url: "{openapi_url}",
            dom_id: '#swagger-ui',
            presets: [SwaggerUIBundle.presets.apis, SwaggerUIStandalonePreset],
            layout: "StandaloneLayout"
        }})
    </script>
</body>
</html>"""

REDOC_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>{title} - ReDoc</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
    <style>body {{ margin: 0; padding: 0; }}</style>
</head>
<body>
    <redoc spec-url='{openapi_url}'></redoc>
    <script src="https://unpkg.com/redoc@latest/bundles/redoc.standalone.js"></script>
</body>
</html>"""


def generate_openapi_schema(
    title: str,
    version: str,
    routes: list[dict],
    description: str = "",
) -> dict:
    """
    Generate an OpenAPI 3.0 schema from registered routes.
    """
    paths = {}

    for route in routes:
        method = route["method"].lower()
        path = route["path"]
        handler = route["handler"]
        name = route.get("name", handler.__name__ if hasattr(handler, "__name__") else "unknown")

        # Convert path params from {param} to standard OpenAPI format
        openapi_path = path

        if openapi_path not in paths:
            paths[openapi_path] = {}

        # Build the operation
        operation = {
            "summary": name.replace("_", " ").title(),
            "operationId": name,
            "responses": {
                "200": {
                    "description": "Successful Response",
                    "content": {
                        "application/json": {
                            "schema": {"type": "object"}
                        }
                    }
                }
            }
        }

        # Extract path parameters
        import re
        param_names = re.findall(r'\{(\w+)\}', path)
        if param_names:
            operation["parameters"] = [
                {
                    "name": p,
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string"}
                }
                for p in param_names
            ]

        # Check handler docstring for description
        if handler.__doc__:
            operation["description"] = handler.__doc__.strip()

        paths[openapi_path][method] = operation

    schema = {
        "openapi": "3.0.0",
        "info": {
            "title": title,
            "version": version,
            "description": description or f"{title} API powered by Ignyx",
        },
        "paths": paths,
    }

    return schema
