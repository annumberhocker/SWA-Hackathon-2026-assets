"""Inject, list, remove, or clear anomalies for the Gate Change Cascade simulator.

Usage:
    # Inject a gate_wait spike on flight AX101
    python -m simulator.anomaly_injector AX101 schedule gate_wait

    # Inject a departure_delay spike with higher intensity
    python -m simulator.anomaly_injector AX303 schedule departure_delay --intensity 4.0

    # Inject a turnaround_time anomaly
    python -m simulator.anomaly_injector AX202 schedule turnaround_time --intensity 3.0

    # List active injections
    python -m simulator.anomaly_injector --list

    # Remove a specific injection
    python -m simulator.anomaly_injector --remove AX101 schedule gate_wait

    # Clear all injections
    python -m simulator.anomaly_injector --clear

Arguments:
    entity_id   Flight number (e.g. AX101, AX202, AX303, AX404)
    stream      Must be: schedule
    metric      One of: departure_delay | gate_wait | turnaround_time
"""

import argparse
import json
import os
import time

ANOMALY_FILE = "/tmp/gcc_anomaly.json"


def _load() -> list[dict]:
    if not os.path.exists(ANOMALY_FILE):
        return []
    try:
        with open(ANOMALY_FILE, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []
    if isinstance(data, list):
        return [t for t in data if isinstance(t, dict)]
    if isinstance(data, dict):
        return [data]
    return []


def _save(targets: list[dict]) -> None:
    if not targets:
        if os.path.exists(ANOMALY_FILE):
            os.remove(ANOMALY_FILE)
        return
    with open(ANOMALY_FILE, "w") as f:
        json.dump(targets, f)


def _key(entity_id: str, stream: str, metric: str) -> tuple:
    return (entity_id, stream, metric)


def inject_anomaly(
    entity_id: str,
    stream: str,
    metric: str,
    intensity: float = 3.0,
    details: dict | None = None,
) -> None:
    """Upsert an anomaly injection by (entity_id, stream, metric)."""
    targets = [
        t for t in _load()
        if _key(t.get("entity_id", ""), t.get("stream", ""), t.get("metric", ""))
        != _key(entity_id, stream, metric)
    ]
    entry = {
        "entity_id":  entity_id,
        "stream":     stream,
        "metric":     metric,
        "start_time": time.time(),
        "intensity":  intensity,
    }
    if details:
        entry["details"] = details
    targets.append(entry)
    _save(targets)
    print(
        f"Injected: {entity_id} / {stream} / {metric} (intensity={intensity}). "
        f"Ramps over ~20 s. {len(targets)} injection(s) active."
    )


def remove_anomaly(entity_id: str, stream: str, metric: str) -> None:
    before = _load()
    after = [
        t for t in before
        if _key(t.get("entity_id", ""), t.get("stream", ""), t.get("metric", ""))
        != _key(entity_id, stream, metric)
    ]
    _save(after)
    if len(after) < len(before):
        print(f"Removed: {entity_id} / {stream} / {metric}. {len(after)} remaining.")
    else:
        print(f"No active injection for {entity_id} / {stream} / {metric}.")


def clear_anomaly() -> None:
    targets = _load()
    _save([])
    print(f"Cleared {len(targets)} injection(s).")


def list_anomalies() -> None:
    targets = _load()
    if not targets:
        print("No active injections.")
        return
    print(f"{len(targets)} active injection(s):")
    for t in targets:
        elapsed = max(0, int(time.time() - t.get("start_time", time.time())))
        print(
            f"  - {t.get('entity_id')} / {t.get('stream')} / {t.get('metric')} "
            f"(x{t.get('intensity')}, {elapsed}s ago)"
        )


def main():
    p = argparse.ArgumentParser(description="Inject or clear Gate Change Cascade anomalies.")
    p.add_argument("entity_id", nargs="?", help="Flight number (e.g. AX101)")
    p.add_argument("stream",    nargs="?", help="Must be: schedule")
    p.add_argument("metric",    nargs="?", help="departure_delay | gate_wait | turnaround_time")
    p.add_argument("--intensity", type=float, default=3.0, help="Anomaly intensity multiplier (default 3.0)")
    p.add_argument("--clear",  action="store_true", help="Remove all active injections")
    p.add_argument("--remove", action="store_true", help="Remove a single injection")
    p.add_argument("--list",   action="store_true", help="Print active injections")
    args = p.parse_args()

    if args.list:
        list_anomalies()
    elif args.clear:
        clear_anomaly()
    elif args.remove and args.entity_id and args.stream and args.metric:
        remove_anomaly(args.entity_id, args.stream, args.metric)
    elif args.entity_id and args.stream and args.metric:
        inject_anomaly(args.entity_id, args.stream, args.metric, args.intensity)
    else:
        p.error("Provide entity_id, stream, and metric; or use --list / --clear / --remove.")


if __name__ == "__main__":
    main()
