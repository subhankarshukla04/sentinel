"""Static-data accessors. Read-through; no caching needed at this scale."""
import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def _load(filename: str):
    with open(os.path.join(DATA_DIR, filename)) as f:
        return json.load(f)


def list_projects() -> list[dict]:
    return _load("sample_projects.json")


def get_project(project_id: str) -> dict | None:
    for p in list_projects():
        if p["id"] == project_id:
            return p
    return None


def _risks_dict() -> dict:
    return _load("known_risks.json")


def known_risks(project_id: str | None) -> dict:
    if not project_id:
        return {"litigation": [], "ngo_complaints": []}
    return _risks_dict().get(project_id, {"litigation": [], "ngo_complaints": []})


def all_risk_entries() -> list[dict]:
    """Risk entries with their key + aliases attached, for fuzzy lookup."""
    out = []
    for k, v in _risks_dict().items():
        entry = dict(v)
        entry["id"] = k
        # aliases come from the project metadata
        proj = get_project(k)
        if proj:
            entry.setdefault("aliases", [])
            entry["aliases"].extend([proj.get("name", ""), proj.get("developer", "")])
        out.append(entry)
    return out
