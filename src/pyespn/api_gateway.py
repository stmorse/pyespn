# api_gateway.py

from __future__ import annotations
from importlib import resources
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Type

import httpx
import yaml
from pydantic import BaseModel

from .models import Team
from .settings import ESPNSettings

# Model registry so the schema can refer to models by name.
MODEL_REGISTRY: Dict[str, Type[BaseModel]] = {
    "Team": Team,
}

@dataclass
class RouteSpec:
    name: str
    path: str
    method: str

@dataclass
class OperationSpec:
    name: str
    route: str
    params: Dict[str, str]
    model_name: Optional[str]
    response_root: Optional[str]
    response_form: str
    field_map: Dict[str, str] = None

    def model(self) -> Optional[Type[BaseModel]]:
        if self.model_name is None:
            return None
        try:
            return MODEL_REGISTRY[self.model_name]
        except KeyError:
            raise KeyError(f"Model '{self.model_name}' not found in MODEL_REGISTRY.")


class APIGateway:
    """
    Gateway that:
      - loads a simple YAML schema,
      - builds URLs from path templates,
      - merges default+override query params,
      - validates responses into pydantic models.
    """

    def __init__(self):
        
        # load schema.yaml next to this module, via package resources
        with resources.files("pyespn").joinpath("schema.yaml").open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        # load settings (currently just cookies) from .env
        settings = ESPNSettings()
    
        # grab base API url from schema
        self.base_url: str = raw["base_url"].rstrip("/")

        # populate _routes with RouteSpec's
        self._routes: Dict[str, RouteSpec] = {}
        for name, spec in raw["routes"].items():
            self._routes[name] = RouteSpec(
                name=name,
                path=spec["path"],
                method=spec.get("method", "GET").upper(),
            )

        # populate _operations with OperationSpec's
        self._operations: Dict[str, OperationSpec] = {}
        for name, spec in raw["operations"].items():
            self._operations[name] = OperationSpec(
                name=name,
                route=spec.get("route"),
                params=spec.get("params", {}),              # url params
                model_name=spec.get("model"),               # str
                response_root=spec.get("response_root", None),
                response_form=spec.get("response_form"),    # list or dict
                field_map=spec.get("field_map", {})
            )

        # single shared client for simplicity
        self._client = httpx.Client(
            timeout=30.0, 
            cookies=settings.cookies or {}
        )

    def close(self) -> None:
        self._client.close()

    # --- Generic request/validate ---
    def request(
            self, 
            operation: str, 
            path_args: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Main workhorse method: 
        - builds API request from schema and sends request
        - converts response to pydantic model and returns
        """

        # get the operation requested
        op = self._get_operation(operation)
        route = self._get_route(op.route)
        url = self._format_url(route.path, path_args or {})

        # send the request and convert to JSON
        resp = self._client.request(route.method, url, params=op.params)
        resp.raise_for_status()
        payload = resp.json()

        # get class (model) of this endpoint (Team, etc) (actual class, not str)
        model_cls = op.model()

        # If no model specified, return raw payload
        if model_cls is None:
            print("No model specified in schema, returning full payload.")
            return payload

        # pull sub-JSON if endpoint specifies a field
        if op.response_root:
            data = payload.get(op.response_root, None)
            if data is None:
                raise KeyError(f"Key '{op.response_root}' not found in '{op.name}'.")
        else:
            data = payload
        
        # get map of: {"our codebase's field": "current espn field"} and remap
        field_map = op.field_map or {}
        _map_item = lambda item: {field_map.get(k,k):v for k,v in item.items()}

        # handle `data` that is a single model
        if op.response_form == "dict" and isinstance(data, dict):
            mapped = _map_item(data)
            return model_cls.model_validate(mapped)

        # handle `data` that is a list of models
        if op.response_form == "list" and isinstance(data, list):
            mapped = [_map_item(x) if isinstance(x, dict) else x for x in data]
            return [model_cls.model_validate(x) for x in mapped]

        # Fallback for non-JSON-object/list responses
        print("Response does not match response type, returning full payload.")
        return payload

    # --- Internals ---
    def _get_route(self, name: str) -> RouteSpec:
        try:
            return self._routes[name]
        except KeyError:
            raise KeyError(f"Operation '{name}' not defined in schema.")

    def _get_operation(self, name: str) -> OperationSpec:
        try:
            return self._operations[name]
        except KeyError:
            raise KeyError(f"Operation '{name}' not defined in schema.")

    def _format_url(self, path_template: str, path_params: Dict[str, Any]) -> str:
        try:
            path = path_template.format(**path_params)
        except KeyError as e:
            raise KeyError(f"Missing path parameter: {e}") from e
        return f"{self.base_url}{path}"
