# api_gateway.py
from __future__ import annotations
from importlib import resources
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Type

import httpx
import yaml
from pydantic import BaseModel, Field, ValidationError


# --- Domain models (stable objects your app uses) ---
class Team(BaseModel):
    name: str
    current_projected_rank: Optional[int] = None

    model_config = {
        "populate_by_name": True,  # allow using both field and alias names
        "extra": "ignore",         # ignore fields the API adds later
    }


# Model registry so the schema can refer to models by name.
MODEL_REGISTRY: Dict[str, Type[BaseModel]] = {
    "Team": Team,
}


@dataclass
class EndpointSpec:
    name: str
    path: str
    method: str
    params: Dict[str, Any]
    response_root: Optional[str]
    model_name: Optional[str]
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
    Minimal adapter/gateway that:
      - loads a simple YAML schema,
      - builds URLs from path templates,
      - merges default+override query params,
      - validates responses into pydantic models.
    """

    def __init__(self, schema_path: str | None = None, cookies: dict | None = None):
        if schema_path is None:
            # load schema.yaml next to this module, via package resources
            with resources.files("pyespn").joinpath("schema.yaml").open("r", encoding="utf-8") as f:
                raw = yaml.safe_load(f)
        else:
            # user passed an explicit path (also fine)
            with open(schema_path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f)

        self.base_url: str = raw["base_url"].rstrip("/")
        self._endpoints: Dict[str, EndpointSpec] = {}

        # populate _endpoints with EndpointSpec's based on the schema.yaml
        for name, spec in raw["endpoints"].items():
            self._endpoints[name] = EndpointSpec(
                name=name,
                path=spec["path"],
                method=spec.get("method", "GET").upper(),  # GET default
                params=spec.get("params", {}) or {},
                response_root=spec.get("response_root"),
                model_name=spec.get("model"),
            )

        # single shared client for simplicity; OK for quick scripts
        self._client = httpx.Client(timeout=30.0, cookies=cookies or {})

    def close(self) -> None:
        self._client.close()

    # --- Generic request/validate ---
    def request(
        self,
        endpoint_name: str,
        *,
        path_params: Optional[Dict[str, Any]] = None,
        query_overrides: Optional[Dict[str, Any]] = None,
        cookies: Optional[Dict[str, str]] = None,
    ) -> Any:
        """
        Generic requester:
        - Builds URL from schema path template + path_params
        - Merges default params from schema with query_overrides
        - Applies schema `field_map` (API key -> domain field) before validation
        - Validates against endpoint's model if provided
        - Supports list or object under `response_root`, or whole-payload validation if no root
        """
        ep = self._get_endpoint(endpoint_name)
        url = self._format_url(ep.path, path_params or {})
        params = {**(ep.params or {}), **(query_overrides or {})}

        resp = self._client.request(ep.method, url, params=params, cookies=cookies)
        resp.raise_for_status()
        payload = resp.json()

        model_cls = ep.model()
        field_map: Dict[str, str] = ep.field_map or {}

        def _map_item(item: Dict[str, Any]) -> Dict[str, Any]:
            # rename API keys -> domain keys per schema; pass through unknowns
            return {field_map.get(k, k): v for k, v in item.items()}

        # If no model specified, return raw payload (schema controls shape later)
        if model_cls is None:
            return payload

        # With a model, figure out what to validate (rooted or whole payload)
        if ep.response_root:
            data = payload.get(ep.response_root, None)
            if data is None:
                raise KeyError(
                    f"Key '{ep.response_root}' not found in response for endpoint '{ep.name}'."
                )

            if isinstance(data, list):
                mapped = [_map_item(x) if isinstance(x, dict) else x for x in data]
                return [model_cls.model_validate(x) for x in mapped]

            if isinstance(data, dict):
                mapped = _map_item(data)
                return model_cls.model_validate(mapped)

            raise TypeError(
                f"Expected list or object at response_root '{ep.response_root}', got {type(data).__name__}."
            )

        # No response_root: validate whole payload (supports object or list-of-objects)
        if isinstance(payload, list):
            mapped = [_map_item(x) if isinstance(x, dict) else x for x in payload]
            return [model_cls.model_validate(x) for x in mapped]

        if isinstance(payload, dict):
            mapped = _map_item(payload)
            return model_cls.model_validate(mapped)

        # Fallback for non-JSON-object/list responses
        return payload


    # --- Friendly helper for your example endpoint ---
    def get_league_teams(
        self, *, season: int, league_id: int, view: Optional[str] = None
    ) -> List[Team]:
        query = {"view": view} if view else {}
        return self.request(
            "get_league_teams",
            path_params={"season": season, "league_id": league_id},
            query_overrides=query,
        )

    # --- Internals ---
    def _get_endpoint(self, name: str) -> EndpointSpec:
        try:
            return self._endpoints[name]
        except KeyError:
            raise KeyError(f"Endpoint '{name}' not defined in schema.")

    def _format_url(self, path_template: str, path_params: Dict[str, Any]) -> str:
        try:
            path = path_template.format(**path_params)
        except KeyError as e:
            raise KeyError(f"Missing path parameter: {e}") from e
        return f"{self.base_url}{path}"
