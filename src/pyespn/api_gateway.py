# api_gateway.py

from __future__ import annotations
import copy
from importlib import resources
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Type

import httpx
import yaml
from pydantic import BaseModel

from .models import Team, Player, MatchupHistorical, RosterMoveResponse
from .settings import ESPNSettings

# Model registry so the schema can refer to models by name.
# NOTE: we only need this for top-level models --> the models may contain 
# sub-models, no need to define here
MODEL_REGISTRY: Dict[str, Type[BaseModel]] = {
    "Team": Team,
    "Player": Player,
    "MatchupHistorical": MatchupHistorical,
    "RosterMoveResponse": RosterMoveResponse
}

@dataclass
class BaseSpec:
    name: str
    url: str
    method: str

@dataclass
class RouteSpec:
    name: str
    path: str
    base: str

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
            raise KeyError(f"Model '{self.model_name}' not in MODEL_REGISTRY.")


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
        ypath = resources.files("pyespn").joinpath("schema.yaml")
        with ypath.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        # load settings (currently just cookies) from .env
        settings = ESPNSettings()

        # populate _bases with BaseSpec's
        self._bases: Dict[str, BaseSpec] = {}
        for name, spec in raw["bases"].items():
            self._bases[name] = BaseSpec(
                name=name,
                url=spec["url"],
                method=spec["method"].upper(),
            )

        # populate _routes with RouteSpec's
        self._routes: Dict[str, RouteSpec] = {}
        for name, spec in raw["routes"].items():
            self._routes[name] = RouteSpec(
                name=name,
                path=spec["path"],
                base=spec["base"],
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
            path_args: Optional[Dict[str, Any]] = None,
            payload: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Main workhorse method: 
        - builds API request from schema and sends request
        - converts response to pydantic model and returns
        """

        # --- GET THE RESPONSE ---

        # get the operation requested
        op = self._get_operation(operation)
        route = self._get_route(op.route)
        base = self._get_base(route.base)
        url = self._format_url(base.url, route.path, path_args or {})

        # send the request and convert to JSON
        resp = self._client.request(
            base.method,        # GET or POST
            url, 
            params=op.params,   # ? params (mView, etc)
            data=payload or {}  # only for POST
        )
        resp.raise_for_status()
        resp = resp.json()

        # get class (model) of this endpoint (Team, etc) (actual class, not str)
        model_cls = op.model()

        # If no model specified, return raw response
        if model_cls is None:
            print("No model specified in schema, returning full payload.")
            return resp

        # pull sub-JSON if endpoint specifies a field
        if op.response_root:
            data = resp.get(op.response_root, None)
            if data is None:
                raise KeyError(f"Key '{op.response_root}' not found in '{op.name}'.")
        else:
            data = resp
        
        
        # --- CONVERT DATA TO MODEL(S) ---
        
        field_map = op.field_map or {}

        # handle `data` that is a single model
        if op.response_form == "dict" and isinstance(data, dict):
            mapped = self._map_item(data, field_map)
            return model_cls.model_validate(mapped)

        # handle `data` that is a list of models
        if op.response_form == "list" and isinstance(data, list):
            mapped = [
                self._map_item(x, field_map) 
                if isinstance(x, dict) else x for x in data
            ]
            return [model_cls.model_validate(x) for x in mapped]

        # Fallback for non-JSON-object/list responses
        print("Response does not match response type, returning full payload.")
        return resp


    # ------------------------------------------------
    # INTERNAL METHODS
    # ------------------------------------------------

    def _get_base(self, name: str) -> BaseSpec:
        try:
            return self._bases[name]
        except KeyError:
            raise KeyError(f"Base '{name}' not defined in schema.")
        
    def _get_route(self, name: str) -> RouteSpec:
        try:
            return self._routes[name]
        except KeyError:
            raise KeyError(f"Route '{name}' not defined in schema.")

    def _get_operation(self, name: str) -> OperationSpec:
        try:
            return self._operations[name]
        except KeyError:
            raise KeyError(f"Operation '{name}' not defined in schema.")

    def _format_url(
            self, 
            base_url: str, 
            path_template: str, 
            path_params: Dict[str, Any]
    ) -> str:
        try:
            path = path_template.format(**path_params)
        except KeyError as e:
            raise KeyError(f"Missing path parameter: {e}") from e
        return f"{base_url}{path}"
    
    def _map_item(self, 
            item: Dict[str, Any], 
            mapping: Dict[str, str]
    ) -> Dict[str, Any]:
        """Handles field_map changes in schema, including nested changes"""

        # NOTE: (OLDER) this doesn't handle nested models so its commented out
        # field_map = op.field_map or {}
        # _map_item = lambda item: {field_map.get(k,k):v for k,v in item.items()}

        # dummy object to signal a missing entry
        _MISSING = object()

        def _get_by_path(obj: Dict[str, Any], path: str) -> Any:
            # start cur as the full API data
            cur = obj

            # path is something like record.overall.pointsFor
            # this traverses down the dict until cur is the value of pointsFor
            # if we run out of dict before we get there, return "_MISSING"
            for seg in path.split("."):
                # if cur is not a dict anymore or this seg is not 
                if not isinstance(cur, dict) or seg not in cur:
                    return _MISSING
                cur = cur[seg]
            return cur

        def _set_by_path(obj: Dict[str, Any], path: str, value: Any) -> None:
            cur = obj
            parts = path.split(".")
            for seg in parts[:-1]:
                nxt = cur.get(seg)
                if not isinstance(nxt, dict):
                    nxt = {}
                    cur[seg] = nxt
                cur = nxt
            cur[parts[-1]] = value

        def _map_item_dotted(
                item: Dict[str, Any], mapping: Dict[str, str]
        ) -> Dict[str, Any]:
            """
            Returns a new dict where any mapping like 'src.a.b' -> 'dst.x.y'
            is applied. Unmapped keys are preserved as-is.
            """

            out = copy.deepcopy(item)
            for src, dst in (mapping or {}).items():
                # val is the value of the end of the dotted map 
                # (like record.overall.pointsFor, val is 123 or whatever)
                val = _get_by_path(item, src)
                
                # if its not missing, we rename `out`` appropriate
                if val is not _MISSING:
                    _set_by_path(out, dst, val)
            
            # return the re-mapped `out`
            return out
        
        return _map_item_dotted(item, mapping)
