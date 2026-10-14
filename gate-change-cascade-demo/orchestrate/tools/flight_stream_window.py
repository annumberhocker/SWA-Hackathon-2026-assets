"""Real-time flight schedule window via the investigator-api.

Calls the shared investigator-api REST bridge to tail the ops-alerts topic
for the last N seconds for a given flight and returns per-metric summaries.
"""

import json
import urllib.parse
import urllib.request

from ibm_watsonx_orchestrate.agent_builder.tools import tool

INVESTIGATOR_API_URL = "__INVESTIGATOR_API_URL__"


@tool(
    name="flight_stream_window",
    description=(
        "Summarize the last N seconds of real-time flight schedule telemetry from Kafka "
        "for a specific flight or aircraft. Metrics: departure_delay, gate_wait, turnaround_time. "
        "Use when asked 'what has the gate wait been in the last 30 seconds?' or for live context."
    ),
)
def flight_stream_window(
    entity_id: str,
    metric: str = "",
    window_seconds: int = 30,
) -> dict:
    """
    Args:
        entity_id: Aircraft ID (e.g. N303AX) or flight number (e.g. AX303).
        metric: Metric name to filter on (departure_delay, gate_wait, turnaround_time).
                Leave blank to return all schedule metrics.
        window_seconds: Look-back window in seconds (default 30).

    Returns:
        Dict with min, max, avg, count, last_value per metric; or an error dict.
    """
    if not INVESTIGATOR_API_URL or INVESTIGATOR_API_URL.startswith("__"):
        return {"status": "error", "error": "INVESTIGATOR_API_URL not configured"}
    params: dict = {
        "entity_id":      entity_id,
        "stream":         "schedule",
        "window_seconds": int(window_seconds),
    }
    if metric:
        params["metric"] = metric
    url = f"{INVESTIGATOR_API_URL.rstrip('/')}/stream_window?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        return {"status": "error", "error": str(exc)}
