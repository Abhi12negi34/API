"""
Prometheus bottleneck identifier — queries the Prometheus endpoint from
config for high-latency or high-error-rate metrics. Falls back to
analysing captured traffic latency if Prometheus is unreachable.
"""
from __future__ import annotations
import requests
from core.api.mock_generator import load_captured_requests, is_api_candidate, generalize_path
from collections import defaultdict


def _load_prometheus_url() -> str:
    try:
        from pathlib import Path
        import yaml
        cfg = yaml.safe_load(
            (Path(__file__).resolve().parents[2] / "config" / "config.yaml")
            .read_text(encoding="utf-8")
        )
        return str(cfg.get("prometheus", {}).get("endpoint", "http://localhost:9090")).rstrip("/")
    except Exception:
        return "http://localhost:9090"


def _query_prometheus(base: str, promql: str, timeout: int = 4):
    try:
        r = requests.get(
            f"{base}/api/v1/query",
            params={"query": promql},
            timeout=timeout, verify=False,
        )
        if r.status_code == 200:
            return r.json().get("data", {}).get("result", [])
    except Exception:
        pass
    return None


def identify_scale_bottlenecks(workspace_root=None):
    print("[SCALABILITY: Bottlenecks] Querying Prometheus for latency and error rate metrics...")

    prom_url = _load_prometheus_url()
    issues = []
    source = "prometheus"

    # Try Prometheus first
    high_latency = _query_prometheus(
        prom_url,
        'histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1'
    )
    high_errors = _query_prometheus(
        prom_url,
        'rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05'
    )

    if high_latency is not None:
        for result in (high_latency or []):
            metric = result.get("metric", {})
            value = result.get("value", [None, None])[1]
            issues.append(
                f"High p95 latency {float(value or 0)*1000:.0f}ms on "
                f"{metric.get('handler') or metric.get('path') or 'unknown'}"
            )
        for result in (high_errors or []):
            metric = result.get("metric", {})
            value = result.get("value", [None, None])[1]
            issues.append(
                f"High error rate {float(value or 0)*100:.1f}% on "
                f"{metric.get('handler') or metric.get('path') or 'unknown'}"
            )
    else:
        # Prometheus unavailable — fall back to captured traffic
        source = "captured_traffic"
        entries = load_captured_requests(workspace_root)
        api_entries = [e for e in entries if is_api_candidate(e)]

        lat_map: dict[str, list[float]] = defaultdict(list)
        for e in api_entries:
            lat = e.get("response_time_ms")
            if isinstance(lat, (int, float)) and lat > 0:
                lat_map[generalize_path(str(e.get("path") or "/"))].append(lat)

        if not lat_map:
            return {
                "success": True, "status": "SKIPPED", "mode": "SIMULATED", "severity": "INFO",
                "log": f"Prometheus unreachable at {prom_url} and no latency data in captured traffic.",
                "recommendation": "Start Prometheus or re-run capture with Phase 0.1 applied.",
            }

        for path, lats in lat_map.items():
            p95 = sorted(lats)[int(len(lats) * 0.95)] if len(lats) >= 2 else lats[0]
            if p95 > 1500:
                issues.append(f"{path}: p95={p95:.0f}ms from {len(lats)} samples")

    success = len(issues) == 0
    return {
        "success": success, "status": "PASS" if success else "FAIL",
        "mode": "LIVE", "severity": "INFO" if success else "HIGH",
        "log": (
            f"No bottlenecks detected via {source}."
            if success else
            f"Bottlenecks ({source}): {'; '.join(issues[:5])}"
        ),
        "recommendation": "Scale horizontally, add caching, or optimise DB queries for flagged endpoints." if not success else "N/A",
        "source": source,
        "issues": issues,
    }
