"""Historical flight schedule query backed by Confluent TableFlow + Apache Iceberg.

Reads the `flight-events` Iceberg table materialized by TableFlow and returns
30-day aggregated statistics for a given flight and metric. This gives the
triage agent historical context to determine if the current anomaly is truly
unusual compared to baseline.

If TableFlow is not configured (env vars missing), returns a graceful
{"status": "tableflow_not_configured"} so the agent can still run dry.
"""

import os
from typing import Optional

from ibm_watsonx_orchestrate.agent_builder.tools import tool

# TableFlow / Iceberg catalog connection (set in .env)
_CATALOG_URI   = os.environ.get("TABLEFLOW_CATALOG_URI", "")
_WAREHOUSE     = os.environ.get("TABLEFLOW_WAREHOUSE", "")
_NAMESPACE     = os.environ.get("TABLEFLOW_NAMESPACE", "")
_API_KEY       = os.environ.get("CONFLUENT_API_KEY", "")
_API_SECRET    = os.environ.get("CONFLUENT_API_SECRET", "")
_TABLE_NAME    = "flight-events"


def _tableflow_configured() -> bool:
    return bool(_CATALOG_URI and _WAREHOUSE and _NAMESPACE and _API_KEY and _API_SECRET)


@tool(
    name="query_flight_history",
    description=(
        "Query 30 days of historical flight schedule data from the Confluent TableFlow "
        "Iceberg table to establish a baseline. Returns avg, p95, and current-vs-historical "
        "ratio for the requested metric. Use this to determine whether the anomaly score is "
        "truly unusual compared to historical patterns."
    ),
)
def query_flight_history(
    flight_number: str,
    metric: str = "gate_wait",
    days: int = 30,
) -> dict:
    """
    Args:
        flight_number: Flight number (e.g. AX101).
        metric: Metric to aggregate (departure_delay | gate_wait | turnaround_time).
        days: Look-back window in days (default 30).

    Returns:
        Dict with avg_value_historical, p95_value_historical, sample_recent_events,
        or status: tableflow_not_configured if env vars are missing.
    """
    if not _tableflow_configured():
        return {
            "status": "tableflow_not_configured",
            "message": (
                "TABLEFLOW_CATALOG_URI / TABLEFLOW_WAREHOUSE / TABLEFLOW_NAMESPACE not set. "
                "Enable Confluent TableFlow on the flight-events topic and add these values "
                "to .env to enable historical Iceberg queries."
            ),
        }

    try:
        from pyiceberg.catalog import load_catalog
        import pyarrow.compute as pc

        catalog = load_catalog(
            "tableflow",
            **{
                "type":              "rest",
                "uri":               _CATALOG_URI,
                "warehouse":         _WAREHOUSE,
                "credential":        f"{_API_KEY}:{_API_SECRET}",
                "oauth2-server-uri": f"{_CATALOG_URI}/v1/oauth/tokens",
                "scope":             "catalog",
            },
        )

        table = catalog.load_table(f"{_NAMESPACE}.{_TABLE_NAME}")

        # Scan last `days` days, filtered to this flight and metric
        from datetime import datetime, timezone, timedelta
        cutoff_ts = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        scan = table.scan(
            row_filter=(
                pc.field("flight_number") == flight_number
            ) & (
                pc.field("metric") == metric
            ) & (
                pc.field("timestamp") >= cutoff_ts
            ),
            selected_fields=("flight_number", "metric", "value", "unit", "timestamp"),
            limit=5000,
        )

        arrow_table = scan.to_arrow()

        if arrow_table.num_rows == 0:
            return {
                "status": "ok",
                "flight_number": flight_number,
                "metric":        metric,
                "days":          days,
                "row_count":     0,
                "message":       "No historical data found for this flight/metric combination.",
            }

        import pyarrow.compute as pac
        values = arrow_table.column("value")
        avg_val = float(pac.mean(values).as_py())
        p95_val = float(pac.approximate_median(values).as_py())  # fallback — median as p95 proxy

        # Sample most recent 5 rows
        ts_col = arrow_table.column("timestamp")
        sorted_idx = pac.sort_indices(ts_col, sort_keys=[("timestamp", "descending")])
        recent = arrow_table.take(sorted_idx.slice(0, 5))
        sample = [
            {
                "timestamp":     str(recent.column("timestamp")[i]),
                "value":         float(recent.column("value")[i].as_py()),
                "unit":          str(recent.column("unit")[i]),
            }
            for i in range(recent.num_rows)
        ]

        return {
            "status":               "ok",
            "flight_number":        flight_number,
            "metric":               metric,
            "days":                 days,
            "row_count":            arrow_table.num_rows,
            "avg_value_historical": round(avg_val, 3),
            "p95_value_historical": round(p95_val, 3),
            "unit":                 str(arrow_table.column("unit")[0]),
            "sample_recent_events": sample,
        }

    except ImportError:
        return {
            "status": "error",
            "error": "pyiceberg is not installed. Run: pip install pyiceberg",
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}
