"""Recent flight schedule anomaly events from the ops-alerts topic
via the investigator-api REST bridge."""

import json
import os
import urllib.error
import urllib.parse
import urllib.request

from ibm_watsonx_orchestrate.agent_builder.tools import tool

API = (os.environ.get("INVESTIGATOR_API_URL") or "__INVESTIGATOR_API_URL__").rstrip("/")


def _get(path: str, params: dict) -> dict:
    if not API or API.endswith("__"):
        return {"status": "error", "error": "INVESTIGATOR_API_URL not configured"}
    qs = "&".join(
        f"{k}={urllib.parse.quote(str(v))}"
        for k, v in params.items()
        if v is not None
    )
    url = f"{API}{path}?{qs}" if qs else f"{API}{path}"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return {
            "status": "error",
            "error": f"HTTP {exc.code}: {exc.read().decode('utf-8', 'replace')[:300]}",
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


@tool(
    name="recent_flight_anomalies",
    description=(
        "Returns recent flight schedule anomaly events from the ops-alerts topic "
        "in the last N hours. Optionally filter by entity_id (aircraft ID or flight number) "
        "and metric name (departure_delay, gate_wait, turnaround_time). "
        "Stream is always 'schedule'."
    ),
)
def recent_flight_anomalies(
    entity_id: str | None = None,
    metric: str | None = None,
    hours: int = 24,
) -> dict:
    """
    Args:
        entity_id: Aircraft ID (N303AX) or flight number (AX303). None = all flights.
        metric: Metric name to filter on. None = all schedule metrics.
        hours: Look-back window in hours (default 24).

    Returns:
        Dict with a list of recent anomaly events and summary counts.
    """
    return _get("/recent_anomalies", {
        "entity_id": entity_id,
        "stream":    "schedule",
        "metric":    metric,
        "hours":     hours,
    })
