"""Sentinel — safeguards / FPIC red-flag screen for carbon-project DD."""
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from flask import Flask, render_template, request, abort

from services import territory, news, registry, risk, score, synth, governance, environmental, fpic
from services.validation import ValidationError, clean_name, clean_coord, clean_country

load_dotenv(override=True)
app = Flask(__name__)


def _resolve_project_from_form(form) -> dict:
    """Build the project dict from either a sample selection or ad-hoc form input."""
    project_id = form.get("project_id")
    if project_id and project_id != "adhoc":
        proj = registry.get_project(project_id)
        if proj:
            return proj
    # ad-hoc path
    name = clean_name(form.get("name"))
    lat, lng = clean_coord(form.get("lat"), form.get("lng"))
    return {
        "id": "adhoc",
        "name": name,
        "country": clean_country(form.get("country")),
        "lat": lat,
        "lng": lng,
        "registry": "ad hoc",
        "type": (form.get("type") or "unspecified").strip()[:80],
        "cached_territories": None,
    }


def _assess(project: dict) -> dict:
    """Fan out the evidence calls in parallel, score, synthesize. Pure function over a project dict."""
    with ThreadPoolExecutor(max_workers=4) as pool:
        f_terr = pool.submit(
            territory.territories_at,
            project["lat"], project["lng"], project.get("cached_territories"),
        )
        f_news = pool.submit(news.adverse_news, project["name"], project.get("country"))
        f_env = pool.submit(environmental.country_environment, project.get("country"))
        f_gov = pool.submit(governance.country_governance, project.get("country"))
        terr = f_terr.result()
        news_res = f_news.result()
        env = f_env.result()
        gov = f_gov.result()

    articles = news_res.get("articles", [])
    risk_bundle = risk.collect(project.get("id"), project["name"], articles)
    litigation = risk_bundle["litigation"]
    ngo = risk_bundle["ngo_complaints"]

    territories = terr.get("territories", [])
    coverage = terr.get("coverage", "unknown")
    fpic_check = fpic.assess_fpic(territories, articles, litigation, ngo, coverage)
    overall = score.overall_risk(
        len(territories), news_res.get("adverse_count", 0),
        len(litigation), len(ngo), coverage,
        env_color=env.get("color"), gov_color=gov.get("color"),
        fpic_color=fpic_check.get("color"),
    )
    note = synth.synthesize(project, territories, articles, litigation, ngo, coverage,
                            env=env, gov=gov)

    return {
        "project": project,
        "territory": terr,
        "territories": territories,
        "news": news_res,
        "articles": articles,
        "litigation": litigation,
        "ngo": ngo,
        "env": env,
        "gov": gov,
        "fpic": fpic_check,
        "overall": overall,
        "note": note,
        "risk_meta": risk_bundle,
    }


@app.route("/")
def index():
    return render_template("index.html", projects=registry.list_projects())


@app.route("/assess", methods=["POST"])
def assess():
    try:
        project = _resolve_project_from_form(request.form)
    except ValidationError as e:
        return render_template("_error.html", error=str(e)), 400
    bundle = _assess(project)
    return render_template("_results.html", **bundle)


@app.route("/api/assess", methods=["POST"])
def api_assess():
    """JSON endpoint — same logic, machine-readable shape."""
    payload = request.get_json(silent=True) or {}
    try:
        project_id = payload.get("project_id")
        if project_id and project_id != "adhoc":
            project = registry.get_project(project_id)
            if not project:
                return {"ok": False, "error": f"unknown project_id: {project_id}"}, 404
        else:
            project = {
                "id": "adhoc",
                "name": clean_name(payload.get("name")),
                "country": clean_country(payload.get("country")),
                "registry": "ad hoc",
                "type": (payload.get("type") or "unspecified")[:80],
                "cached_territories": None,
            }
            project["lat"], project["lng"] = clean_coord(payload.get("lat"), payload.get("lng"))
    except ValidationError as e:
        return {"ok": False, "error": str(e)}, 400

    bundle = _assess(project)
    # strip non-serializable bits
    return {
        "ok": True,
        "project": bundle["project"],
        "verdict": bundle["overall"],
        "territory": {
            "source": bundle["territory"].get("source"),
            "coverage": bundle["territory"].get("coverage"),
            "territories": bundle["territories"],
        },
        "news": {
            "sources_used": bundle["news"].get("sources_used"),
            "total": bundle["news"].get("total"),
            "adverse_count": bundle["news"].get("adverse_count"),
            "articles": bundle["articles"],
        },
        "litigation": bundle["litigation"],
        "ngo_complaints": bundle["ngo"],
        "environmental": bundle["env"],
        "governance": bundle["gov"],
        "fpic": bundle["fpic"],
        "synthesis": bundle["note"],
    }


@app.route("/healthz")
def healthz():
    return {"ok": True, "service": "sentinel", "version": "0.3"}


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5099, debug=True)
