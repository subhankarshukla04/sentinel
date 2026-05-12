"""Shared HTTP helpers — retry, backoff, sane defaults.

Centralized so every external call has the same behaviour: identifies itself
as Sentinel (so any provider can rate-limit us deliberately rather than
suspiciously), retries idempotent GETs, and never raises out of the call site.
"""
import time
import requests

UA = "Sentinel-CarbonDD/0.2 (+https://github.com/qatalyst-interview-demo)"
DEFAULT_TIMEOUT = 5.0


def get_json(url: str, params: dict | None = None, timeout: float = DEFAULT_TIMEOUT, retries: int = 0, backoff: float = 0.8) -> dict:
    """GET a JSON endpoint with retry. Returns {ok, data?, error?, status?}."""
    last_err = None
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, params=params, timeout=timeout, headers={"User-Agent": UA})
            if r.status_code == 200:
                if not r.text.strip():
                    return {"ok": True, "data": None, "status": 200}
                # Some APIs return text errors with 200 status; sniff it
                stripped = r.text.lstrip()
                if not stripped.startswith(("{", "[")):
                    snippet = stripped[:200].strip()
                    if any(w in snippet.lower() for w in ("error", "limit", "please", "denied")):
                        return {"ok": False, "error": snippet, "status": 200}
                try:
                    return {"ok": True, "data": r.json(), "status": 200}
                except ValueError as e:
                    return {"ok": False, "error": f"invalid json: {e}", "status": 200}
            elif r.status_code in (429, 503, 504) and attempt < retries:
                time.sleep(backoff * (attempt + 1))
                continue
            else:
                return {"ok": False, "error": f"http {r.status_code}", "status": r.status_code, "body": r.text[:300]}
        except (requests.Timeout, requests.ConnectionError) as e:
            last_err = str(e)
            if attempt < retries:
                time.sleep(backoff * (attempt + 1))
                continue
        except Exception as e:
            return {"ok": False, "error": f"{type(e).__name__}: {e}"}
    return {"ok": False, "error": last_err or "exhausted retries"}


def get_text(url: str, params: dict | None = None, timeout: float = DEFAULT_TIMEOUT, retries: int = 0, backoff: float = 0.8) -> dict:
    """GET a text/XML endpoint with retry. Returns {ok, text?, error?, status?}."""
    last_err = None
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, params=params, timeout=timeout, headers={"User-Agent": UA})
            if r.status_code == 200:
                return {"ok": True, "text": r.text, "status": 200}
            elif r.status_code in (429, 503, 504) and attempt < retries:
                time.sleep(backoff * (attempt + 1))
                continue
            else:
                return {"ok": False, "error": f"http {r.status_code}", "status": r.status_code}
        except (requests.Timeout, requests.ConnectionError) as e:
            last_err = str(e)
            if attempt < retries:
                time.sleep(backoff * (attempt + 1))
                continue
        except Exception as e:
            return {"ok": False, "error": f"{type(e).__name__}: {e}"}
    return {"ok": False, "error": last_err or "exhausted retries"}
