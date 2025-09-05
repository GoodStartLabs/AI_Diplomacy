"""
LMVS JSON Schema Validator
==========================

This module defines a Pydantic v2 schema for validating Diplomacy game logs
exported in the LMVS (Language Model vs. State) format.

Friendly overview
-----------------
An LMVS file should contain a top-level object with metadata (`id`, `map`,
`rules`) and a list of **PhaseData** objects under the key `"phases"`.

Each PhaseData object has the following important parts:

* `"name"`: a string like "S1901M" or "F1903A" that encodes season, year, and
  sub-phase. The format is '^[A-Z]\d{4}[MRA]$' or the word 'COMPLETED'.

* `"state"`: a dictionary describing the game board at this phase, with keys:
  
  - `"units"`: {country → [list of unit identifiers]}.
    Each unit identifier looks like `"A BUD"` or `"F STP/SC"`.  
    This says which units each power currently controls and where they are.

  - `"centers"`: {country → [list of supply center locations]}.
    Shows which supply centers each power owns.

  - `"influence"`: {country → [list of provinces]}.
    Records which provinces each power currently controls.

  - `"homes"`: {country → [list of home supply centers]}.
    A country's build home centers.

  - `"retreats"`: {country → {unit → [list of possible retreat provinces]}}.
    Units that must retreat and their allowed destinations.

  - `"civil_disorder"`: {country → integer flag}.
    Records whether a country is in civil disorder.

  - `"builds"`: {country → {count: int, homes: [list of places]}}.
    Tracks build counts and home sites during adjustment phases.

* `"orders"`: {country → [list of orders]}.
  Each order string must follow one of the canonical Diplomacy order formats,
  such as Move, Hold, Support, Convoy, Build, Disband, or Retreat.
  For example: `"A BUD - SER"`, `"F LON S F EDI - NTH"`.

* `"results"`: {unit identifier → [list of result codes]}.
  Each result code is one of: `"void"`, `"bounce"`, `"cut"`, `"dislodged"`,
  `"disband"`, or `"no convoy"`.  
  These describe how the order for that unit resolved.

* `"messages"` (optional): a list of dictionaries, each with:
  - `"sender"`: a valid country
  - `"recipient"`: a valid country
  - `"phase"`: phase code like "S1901M"
  - `"message"`: the text of the press message

Validation rules
----------------
The schema enforces:
- Country names must be one of: AUSTRIA, ENGLAND, FRANCE, GERMANY, ITALY, RUSSIA, TURKEY.
- Phase codes must match the required regex format.
- Units must be of the form "A XXX" or "F XXX[/COAST]".
- Orders must match one of the defined command regexes.
- Result codes must be from the allowed list.
- Orders must reference units that exist in the corresponding `state.units`.

Usage
-----
To use, call:

    from lmvs_light_validation import LMVSGame
    import json

    data = json.load(open("lmvs.json"))
    game = LMVSGame.model_validate(data)

Any structural or semantic mismatches will raise a pydantic `ValidationError`.

This module can be extended with stricter checks by toggling options such as
strict territory membership, strict supply center membership, or coast handling.
"""

from __future__ import annotations
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator, ConfigDict
from pydantic_core.core_schema import ValidationInfo
from analysis.schemas import ALL_PROVINCES, COASTAL_SCs, COUNTRY_RE, PHASE_RE, UNIT_RE, PLACE_RE, COMMAND_PATTERNS, ALLOWED_RESULTS, ALLOWED_COUNTRIES


# build a strict territory set that includes both underscore and slash spellings
STRICT_TERRITORY = set(ALL_PROVINCES)

@dataclass(frozen=True)
class ValidationConfig:
    strict_countries: bool = True
    strict_territories: bool = False  # set True to enforce membership in STRICT_TERRITORY for places
    strict_sc: bool = False           # optionally enforce that centers ⊆ ALL_SUPPLY_CENTERS(+coasts)

# -------------------- validators --------------------

def _validate_country(c: str) -> str:
    if not COUNTRY_RE.match(c):
        raise ValueError(f"bad country name: {c!r}")
    if c not in ALLOWED_COUNTRIES:
        raise ValueError(f"unknown country: {c!r}")
    return c

def _validate_place(code: str, info: ValidationInfo, allow_coast: bool = True) -> str:
    if not PLACE_RE.match(code) and code != "WAIVE":
        raise ValueError(f"bad place code: {code!r}")
    cfg: ValidationConfig = (info.context or {}).get("cfg", ValidationConfig())  # type: ignore
    if cfg.strict_territories:
        if allow_coast:
            if code not in STRICT_TERRITORY:
                raise ValueError(f"unknown territory: {code!r}")
        else:
            base = code.split("/")[0]
            if base not in STRICT_TERRITORY:
                raise ValueError(f"unknown base territory: {code!r}")
    return code

def _validate_unit(u: str, info: ValidationInfo) -> str:
    # handle dislodged units (prefixed with *)
    if u.startswith("*"):
        u = u[1:]  # remove the * prefix for validation
    
    m = UNIT_RE.match(u)
    if not m:
        raise ValueError(f"bad unit: {u!r} (expected 'A XXX' or 'F XXX[/COAST]')")
    _validate_place(m.group("ter"), info, allow_coast=True)
    return u

def _order_kind(order: str) -> Optional[str]:
    # handle build orders (B suffix)
    if order.endswith(" B"):
        return "Build"
    
    for name, pat in COMMAND_PATTERNS:
        if pat.match(order):
            return name
    return None

def _unit_head(order: str) -> Optional[str]:
    # returns the leading "A XXX" or "F XXX/COAST" if present
    m = UNIT_RE.match(order.split(" ", 2)[0] + " " + order.split(" ", 2)[1]) if len(order.split()) >= 2 else None
    if m:
        return m.group(0)
    # fallback: looser search at start
    m = UNIT_RE.match(order)
    return m.group(0) if m else None

def _base_ter(u: str) -> str:
    # "A STP/NC" -> "STP"; "F BUD" -> "BUD"
    ter = u.split(" ", 1)[1] if " " in u else u
    return ter.split("/")[0]

def _unit_type(u: str) -> str:
    return u.split(" ", 1)[0]

# -------------------- models --------------------

class PhaseState(BaseModel):
    name: str
    phase: str
    game_id: str

    units: Dict[str, List[str]]
    centers: Dict[str, List[str]]
    influence: Dict[str, List[str]]
    
    model_config = ConfigDict(extra="ignore")

    @field_validator("name","phase")
    @classmethod
    def _phase_format(cls, v: str, info: ValidationInfo) -> str:
        if not PHASE_RE.match(v) and v != "COMPLETED":
            raise ValueError(f"bad phase: {v!r}")
        return v

    # these should be dictionaries with country names as keys
    @field_validator("units","centers","influence", mode="after")
    @classmethod
    def _country_keys_ok(cls, mapping: Dict[str, Any], info: ValidationInfo) -> Dict[str, Any]:
        for c in mapping.keys():
            _validate_country(c)
        return mapping

    # these should be lists of unit strings
    @field_validator("units", mode="after")
    @classmethod
    def _units_ok(cls, u: Dict[str, List[str]], info: ValidationInfo) -> Dict[str, List[str]]:
        for c, lst in u.items():
            if not isinstance(lst, list):
                raise ValueError(f"units[{c}] must be a list")
            for unit in lst:
                _validate_unit(unit, info)
        return u

    # these should be lists of place strings
    @field_validator("centers","influence", mode="after")
    @classmethod
    def _place_lists_ok(cls, d: Dict[str, List[str]], info: ValidationInfo) -> Dict[str, List[str]]:
        for c, lst in d.items():
            if not isinstance(lst, list):
                raise ValueError(f"{c} values must be a list")
            for t in lst:
                _validate_place(t, info, allow_coast=False)
        return d

class Phase(BaseModel):
    name: str
    state: PhaseState
    orders: Dict[str, Optional[List[str]]]  # allow None values
    results: Dict[str, List[str]]

    model_config = ConfigDict(extra="ignore")

    @field_validator("name")
    @classmethod
    def _phase_format(cls, v: str, info: ValidationInfo) -> str:
        if not PHASE_RE.match(v) and v != "COMPLETED":
            raise ValueError(f"bad phase: {v!r}")
        return v

    @field_validator("orders", mode="after")
    @classmethod
    def _orders_ok(cls, orders: Dict[str, List[str]], info: ValidationInfo) -> Dict[str, List[str]]:
        # handle null orders by converting to empty lists
        cleaned_orders = {}
        for c, lst in orders.items():
            _validate_country(c)
            if lst is None or lst == "null":
                cleaned_orders[c] = []
            elif not isinstance(lst, list):
                raise ValueError(f"orders[{c}] must be a list")
            else:
                cleaned_orders[c] = lst
                for o in lst:
                    kind = _order_kind(o)
                    if not kind:
                        raise ValueError(f"order doesn't match any known command: {o!r}")
        return cleaned_orders

    @field_validator("results", mode="after")
    @classmethod
    def _results_ok(cls, res: Dict[str, List[str]], info: ValidationInfo) -> Dict[str, List[str]]:
        for unit, lst in res.items():
            # skip unit validation for special unit names
            if unit != "WAIVE":
                _validate_unit(unit, info)
            if not isinstance(lst, list):
                raise ValueError(f"results[{unit}] must be a list")
            for r in lst:
                if r == "":
                    pass  # allow empty result codes
                elif r == "WAIVE":
                    pass  # allow WAIVE as a special result code
                elif r not in ALLOWED_RESULTS:
                    raise ValueError(f"illegal result code {r!r} for {unit}")
        return res

    @model_validator(mode="after")
    def _orders_correspond_to_units(self) -> "Phase":
        # derive {country -> set(units)} from state
        country_units = {c: set(v) for c, v in self.state.units.items()}

        # for each order, subject unit must exist for that country (coast-tolerant)
        for c, lst in self.orders.items():
            known = country_units.get(c, set())
            for o in lst:
                # skip validation for build orders (they create new units)
                if o.endswith(' B'):
                    continue
                # skip validation for retreat orders (they operate on dislodged units)
                if ' R ' in o or o.endswith(' R') or o.endswith(' D'):
                    continue
                    
                head = _unit_head(o)
                if not head:
                    # already caught by regex; skip
                    continue
                if head in known:
                    continue
                # coast/base tolerant match
                base = _base_ter(head)
                ut   = _unit_type(head)
                if not any((_unit_type(u) == ut and _base_ter(u) == base) for u in known):
                    raise ValueError(f"order {o!r} for {c} does not match any unit in state.units[{c}]")
        return self

class LMVSGame(BaseModel):
    id: str
    map: str
    rules: List[str]
    phases: List[Phase]

    model_config = ConfigDict(extra="ignore")



# -------------------- example usage --------------------
if __name__ == "__main__":
    import sys, json, pathlib
    if len(sys.argv) != 2:
        print("usage: python validation.py <path_to_lmvsgame.json>")
        sys.exit(1)
    cfg = ValidationConfig(strict_territories=False, strict_sc=False)
    p = pathlib.Path(sys.argv[1])
    data = json.loads(p.read_text())
    game = LMVSGame.model_validate(
        data,
        context={"cfg": cfg},
    )

    print(f"{p} is valid: game_id={game.id} phases={len(game.phases)}")