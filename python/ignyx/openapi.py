"""
OpenAPI schema generation and Swagger UI / ReDoc serving.
Auto-generates OpenAPI 3.1.0 schema from registered routes.
Supports advanced Pydantic model parsing, docstring extraction, and response schemas.
"""

import inspect
import re
from typing import Any, Dict, List, Optional, Type, Union, get_args, get_origin

try:
    from pydantic import BaseModel as _PydanticBaseModel
    _PYDANTIC_AVAILABLE = True
except ImportError:
    _PydanticBaseModel = None  # type: ignore[assignment, misc]
    _PYDANTIC_AVAILABLE = False


def generate_openapi_schema(
    title: str,
    version: str,
    routes: List[Dict[str, Any]],
    description: str = "",
) -> Dict[str, Any]:
    """
    Generate an OpenAPI 3.1.0 schema from registered routes.
    Automatically parses Pydantic models, docstrings, and type hints.
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

        # Parse docstring for summary and description
        summary, doc_description = _parse_docstring(handler.__doc__ or "")
        if not summary:
            summary = name.replace("_", " ").title()

        # Build the operation
        operation: Dict[str, Any] = {
            "summary": summary,
            "operationId": name,
            "responses": {},
        }

        if tags:
            operation["tags"] = tags

        if doc_description:
            operation["description"] = doc_description

        # Extract parameters and body schema using inspect
        sig = inspect.signature(handler)
        parameters: List[Dict[str, Any]] = []
        path_params = re.findall(r"\{(\w+)\}", path)

        has_body = False
        response_model: Optional[type] = None

        # Check return annotation for response model
        if sig.return_annotation and sig.return_annotation is not inspect.Signature.empty:
            response_model = _extract_response_model(sig.return_annotation)

        for param_name, param in sig.parameters.items():
            if param_name in ["request", "background_tasks"]:
                continue

            annotation = param.annotation
            is_path = param_name in path_params

            # Check if this is a Pydantic model (body parameter)
            if _is_pydantic_model(annotation):
                has_body = True
                model_name = getattr(annotation, "__name__", "BodyModel")
                if model_name not in components["schemas"]:
                    components["schemas"][model_name] = _get_model_schema(annotation)

                operation["requestBody"] = {
                    "content": {
                        "application/json": {"schema": {"$ref": f"#/components/schemas/{model_name}"}}
                    },
                    "required": param.default is inspect.Parameter.empty,
                }
                continue

            if is_path:
                parameters.append(
                    {
                        "name": param_name,
                        "in": "path",
                        "required": True,
                        "schema": _get_type_schema(annotation, components),
                    }
                )
            else:
                # Query parameter
                param_schema = _get_type_schema(annotation, components)
                param_def: Dict[str, Any] = {
                    "name": param_name,
                    "in": "query",
                    "required": param.default is inspect.Parameter.empty,
                    "schema": param_schema,
                }
                
                # Add default value if present
                if param.default is not inspect.Parameter.empty and param.default is not None:
                    param_def["schema"]["default"] = param.default
                    
                parameters.append(param_def)

        if parameters:
            operation["parameters"] = parameters

        # Build response schema
        if response_model and _is_pydantic_model(response_model):
            model_name = getattr(response_model, "__name__", "ResponseModel")
            if model_name not in components["schemas"]:
                components["schemas"][model_name] = _get_model_schema(response_model)
            
            operation["responses"]["200"] = {
                "description": "Successful Response",
                "content": {
                    "application/json": {"schema": {"$ref": f"#/components/schemas/{model_name}"}}
                },
            }
        else:
            operation["responses"]["200"] = {
                "description": "Successful Response",
                "content": {"application/json": {"schema": {"type": "object"}}},
            }

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


def _parse_docstring(docstring: str) -> tuple[str, str]:
    """
    Parse a docstring into summary and description.
    First line is summary, rest is description.
    """
    if not docstring:
        return "", ""
    
    lines = docstring.strip().split("\n", 1)
    summary = lines[0].strip()
    description = lines[1].strip() if len(lines) > 1 else ""
    
    return summary, description


def _is_pydantic_model(annotation: Any) -> bool:
    """Check if an annotation is a Pydantic BaseModel."""
    if not _PYDANTIC_AVAILABLE or _PydanticBaseModel is None:
        return False
    try:
        return isinstance(annotation, type) and issubclass(annotation, _PydanticBaseModel)
    except TypeError:
        return False


def _get_model_schema(model_cls: Any) -> Dict[str, Any]:
    """Get JSON schema from a Pydantic model class."""
    fn = getattr(model_cls, "model_json_schema", None)
    if callable(fn):
        result: Dict[str, Any] = fn()
        return result
    return {"type": "object"}


def _extract_response_model(annotation: Any) -> Optional[Type[Any]]:
    """Extract the response model from return type annotation."""
    # Handle Optional[Model] or Union[Model, None]
    origin = get_origin(annotation)
    if origin is Union:
        args = get_args(annotation)
        # Filter out None
        model_args = [arg for arg in args if arg is not type(None)]
        if model_args and _is_pydantic_model(model_args[0]):
            cls: Type[Any] = model_args[0]
            return cls
    
    if _is_pydantic_model(annotation):
        cls2: Type[Any] = annotation
        return cls2
    
    return None


def _get_type_schema(annotation: Any, components: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert Python type annotations to OpenAPI schemas.
    Handles Optional, Union, List, and Pydantic models.
    """
    # Handle None or missing annotation
    if annotation is inspect.Parameter.empty or annotation is None:
        return {"type": "string"}
    
    # Handle Optional types (Union with None)
    origin = get_origin(annotation)
    if origin is Union:
        args = get_args(annotation)
        # Filter out None
        non_none_args = [arg for arg in args if arg is not type(None)]
        if non_none_args:
            schema = _get_type_schema(non_none_args[0], components)
            # Mark as nullable if None was in the Union
            if type(None) in args:
                schema["nullable"] = True
            return schema
    
    # Handle List types
    if origin is list or annotation is list:
        args = get_args(annotation)
        item_schema = _get_type_schema(args[0], components) if args else {"type": "string"}
        return {"type": "array", "items": item_schema}
    
    # Handle basic types
    if annotation is str:
        return {"type": "string"}
    if annotation is int:
        return {"type": "integer"}
    if annotation is float:
        return {"type": "number"}
    if annotation is bool:
        return {"type": "boolean"}
    
    # Handle Pydantic models
    if _is_pydantic_model(annotation):
        model_name = getattr(annotation, "__name__", "Model")
        if model_name not in components["schemas"]:
            components["schemas"][model_name] = _get_model_schema(annotation)
        return {"$ref": f"#/components/schemas/{model_name}"}
    
    # Default fallback
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
