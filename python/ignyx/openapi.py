"""
OpenAPI schema generation and Swagger UI / ReDoc serving.
Auto-generates OpenAPI 3.0 schema from registered routes.
"""

import inspect
import re
from typing import Any, Dict, List

try:
    from pydantic import BaseModel
except ImportError:
    BaseModel = None  # type: ignore


def generate_openapi_schema(
    title: str,
    version: str,
    routes: List[Dict[str, Any]],
    description: str = "",
) -> Dict[str, Any]:
    """
    Generate an OpenAPI 3.0 schema from registered routes.
    """
    paths: Dict[str, Any] = {}
    components: Dict[str, Any] = {"schemas": {}}

    for route in routes:
        method = route["method"].lower()
        path = route["path"]
        handler = route["handler"]
        tags = route.get("tags", [])
        name = route.get("name", handler.__name__ if hasattr(handler, "__name__") else "unknown")

        # Convert path params from {param} to standard OpenAPI format
        openapi_path = path

        if openapi_path not in paths:
            paths[openapi_path] = {}

        # Build the operation
        operation: Dict[str, Any] = {
            "summary": name.replace("_", " ").title(),
            "operationId": name,
            "responses": {
                "200": {
                    "description": "Successful Response",
                    "content": {"application/json": {"schema": {"type": "object"}}},
                }
            },
        }

        if tags:
            operation["tags"] = tags

        # Check handler docstring for description
        if handler.__doc__:
            operation["description"] = handler.__doc__.strip()

        # Extract parameters using inspect
        sig = inspect.signature(handler)
        parameters = []
        path_params = re.findall(r"\{(\w+)\}", path)

        has_body = False

        for param_name, param in sig.parameters.items():
            if param_name in ["request", "background_tasks"]:
                continue

            annotation = param.annotation
            is_path = param_name in path_params

            if param_name == "body" or (
                BaseModel and isinstance(annotation, type) and issubclass(annotation, BaseModel)
            ):
                has_body = True
                model_name = annotation.__name__ if hasattr(annotation, "__name__") else "BodyModel"
                if BaseModel and isinstance(annotation, type) and issubclass(annotation, BaseModel):
                    if model_name not in components["schemas"]:
                        components["schemas"][model_name] = annotation.model_json_schema()

                    operation["requestBody"] = {
                        "content": {
                            "application/json": {"schema": {"$ref": f"#/components/schemas/{model_name}"}}
                        },
                        "required": True,
                    }
                else:
                    operation["requestBody"] = {
                        "content": {"application/json": {"schema": {"type": "object"}}},
                        "required": True,
                    }
                continue

            if is_path:
                parameters.append(
                    {
                        "name": param_name,
                        "in": "path",
                        "required": True,
                        "schema": _get_type_schema(annotation),
                    }
                )
            else:
                # Query parameter
                parameters.append(
                    {
                        "name": param_name,
                        "in": "query",
                        "required": param.default is inspect.Parameter.empty,
                        "schema": _get_type_schema(annotation),
                    }
                )

        if parameters:
            operation["parameters"] = parameters

        if has_body:
            operation["responses"]["422"] = {
                "description": "Validation Error",
                "content": {"application/json": {"schema": {"type": "object"}}},
            }

        paths[openapi_path][method] = operation

    schema = {
        "openapi": "3.1.0",
        "info": {
            "title": title,
            "version": version,
            "description": description or f"{title} API powered by Ignyx",
        },
        "paths": paths,
        "components": components,
    }

    return schema


def _get_type_schema(annotation: Any) -> Dict[str, Any]:
    "Helper to convert Python type annotations to OpenAPI schemas."
    if annotation is str:
        return {"type": "string"}
    if annotation is int:
        return {"type": "integer"}
    if annotation is float:
        return {"type": "number"}
    if annotation is bool:
        return {"type": "boolean"}
    if annotation is list or getattr(annotation, "__origin__", None) is list:
        return {"type": "array", "items": {"type": "string"}}
    return {"type": "string"}


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
