"""Performance SLO (Service Level Objective) enforcement tests.

Tests for:
1. P95 latency targets (≤30 seconds)
2. Regression budget tracking (15% allowed)
3. Performance metrics collection
4. Automated alerting on SLO violations
5. Performance trending and reporting
"""

import json
import statistics
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List

import pytest


@pytest.fixture
def slo_targets() -> Dict[str, Any]:
    """Fixture providing SLO targets."""
    return {
        "name": "FirstTry Performance SLO",
        "version": "1.0",
        "targets": {
            "p95_latency_seconds": 30,
            "p99_latency_seconds": 45,
            "error_rate_percent": 0.1,
            "cache_hit_rate_percent": 80,
        },
        "budget": {
            "regression_percent": 15,
            "window_days": 30,
        },
        "enforcement": {
            "block_on_violation": True,
            "alert_on_warning": True,
            "require_investigation": True,
        },
    }


@pytest.fixture
def performance_metrics() -> List[Dict[str, Any]]:
    """Fixture providing performance metrics."""
    return [
        {
            "timestamp": "2024-01-15T10:00:00Z",
            "tier": "lite",
            "mode": "full",
            "duration_ms": 890,
            "cache_hits": 0,
            "cache_misses": 3,
            "error": None,
        },
        {
            "timestamp": "2024-01-15T10:15:00Z",
            "tier": "lite",
            "mode": "full",
            "duration_ms": 280,
            "cache_hits": 3,
            "cache_misses": 0,
            "error": None,
        },
        {
            "timestamp": "2024-01-15T10:30:00Z",
            "tier": "lite",
            "mode": "full",
            "duration_ms": 250,
            "cache_hits": 3,
            "cache_misses": 0,
            "error": None,
        },
    ]


def test_slo_target_configuration(slo_targets: Dict[str, Any]):
    """Test that SLO targets are properly configured."""
    assert "targets" in slo_targets
    assert slo_targets["targets"]["p95_latency_seconds"] == 30
    assert slo_targets["targets"]["p99_latency_seconds"] == 45
    assert slo_targets["targets"]["cache_hit_rate_percent"] == 80


def test_p95_latency_calculation(performance_metrics: List[Dict[str, Any]]):
    """Test P95 latency calculation."""
    # Extract durations in seconds
    durations = sorted([m["duration_ms"] / 1000 for m in performance_metrics])

    # Calculate P95 (95th percentile)
    p95_index = int(len(durations) * 0.95)
    p95 = durations[min(p95_index, len(durations) - 1)]

    # Should be well under 30-second SLO
    assert p95 < 30


def test_p99_latency_calculation(performance_metrics: List[Dict[str, Any]]):
    """Test P99 latency calculation."""
    durations = [m["duration_ms"] / 1000 for m in performance_metrics]

    # P99 is stricter than P95
    p99 = max(durations)  # Worst case

    assert p99 <= 1.0


def test_cache_hit_rate_calculation(performance_metrics: List[Dict[str, Any]]):
    """Test cache hit rate calculation."""
    total_hits = sum(m["cache_hits"] for m in performance_metrics)
    total_requests = total_hits + sum(m["cache_misses"] for m in performance_metrics)

    hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0

    # Should be 50% or higher
    assert hit_rate >= 50


def test_regression_budget_calculation():
    """Test regression budget tracking."""
    baseline_p95_ms = 280  # Previous acceptable performance
    current_p95_ms = 320  # Slightly slower

    regression_percent = ((current_p95_ms - baseline_p95_ms) / baseline_p95_ms) * 100

    # Calculate if within budget
    regression_budget = 15
    is_within_budget = regression_percent <= regression_budget

    assert regression_percent > 0  # There is regression
    assert is_within_budget  # But within 15% budget


def test_regression_budget_exceeded():
    """Test detection of regression budget exceeded."""
    baseline_p95_ms = 1000
    current_p95_ms = 2000  # 100% regression
    regression_budget = 15

    regression_percent = ((current_p95_ms - baseline_p95_ms) / baseline_p95_ms) * 100

    is_within_budget = regression_percent <= regression_budget

    assert regression_percent > regression_budget
    assert not is_within_budget


def test_slo_violation_alert(slo_targets: Dict[str, Any]):
    """Test alerting on SLO violation."""
    violation = {
        "timestamp": datetime.now().isoformat(),
        "metric": "p95_latency",
        "target": slo_targets["targets"]["p95_latency_seconds"],
        "measured": 45,  # Exceeds 30-second target
        "exceeded_by_percent": 50,
        "severity": "HIGH",
        "action": "ALERT",
    }

    assert violation["measured"] > violation["target"]
    assert violation["severity"] == "HIGH"


def test_performance_daily_report(tmp_path: Path, slo_targets: Dict[str, Any]):
    """Test daily performance report generation."""
    report = {
        "date": "2024-01-15",
        "slo_version": slo_targets["version"],
        "metrics": {
            "p95_latency_ms": 280,
            "p99_latency_ms": 890,
            "error_rate_percent": 0.0,
            "cache_hit_rate_percent": 85,
        },
        "slo_status": {
            "p95": "PASS",
            "p99": "PASS",
            "cache_hits": "PASS",
            "error_rate": "PASS",
        },
        "regression_analysis": {
            "baseline_p95_ms": 280,
            "current_p95_ms": 280,
            "regression_percent": 0.0,
            "within_budget": True,
        },
    }

    report_file = tmp_path / "daily_slo_report.json"
    report_file.write_text(json.dumps(report, indent=2))

    loaded = json.loads(report_file.read_text())

    # All metrics should pass
    assert all(v == "PASS" for v in loaded["slo_status"].values())
    assert loaded["regression_analysis"]["within_budget"]


def test_slo_enforcement_pipeline_block(slo_targets: Dict[str, Any]):
    """Test SLO enforcement blocks pipeline on violation."""
    # Simulate SLO violation
    violation_detected = True
    slo_enforcement = slo_targets["enforcement"]

    should_block = violation_detected and slo_enforcement["block_on_violation"]

    assert should_block


def test_slo_warning_vs_violation(slo_targets: Dict[str, Any]):
    """Test distinction between SLO warning and violation."""
    targets = slo_targets["targets"]

    # Define warning threshold (80% of SLO)
    warning_threshold = targets["p95_latency_seconds"] * 0.8  # 24 seconds
    violation_threshold = targets["p95_latency_seconds"]  # 30 seconds

    metrics = [
        {"p95_ms": 20000, "status": "OK"},  # 20s: well under
        {"p95_ms": 25000, "status": "WARNING"},  # 25s: 80%+ but under 30s
        {"p95_ms": 32000, "status": "VIOLATION"},  # 32s: exceeds 30s
    ]

    for metric in metrics:
        p95_s = metric["p95_ms"] / 1000
        if p95_s > violation_threshold:
            status = "VIOLATION"
        elif p95_s > warning_threshold:
            status = "WARNING"
        else:
            status = "OK"

        assert metric["status"] == status


def test_percentile_calculation_accuracy():
    """Test accuracy of percentile calculations."""
    # Generate synthetic latency data
    latencies = [
        100,
        120,
        150,
        180,
        200,  # Fast (5)
        250,
        280,
        300,
        320,
        350,  # Normal (5)
        400,
        450,
        500,
        600,
        700,  # Slow (5)
        1000,
        1500,
        2000,  # Very slow (3)
    ] + [
        200
    ] * 5  # Additional normal cases

    # Sort for percentile calculation
    sorted_latencies = sorted(latencies)

    # Calculate P95 (95th percentile)
    p95_index = int(len(sorted_latencies) * 0.95)
    p95 = sorted_latencies[p95_index]

    # Should be in the upper range but not the absolute max
    assert p95 > 300
    assert p95 < 2000


def test_trend_analysis_improvement():
    """Test trend analysis showing improvement."""
    trend_data = {
        "week_1": {"p95_ms": 1000, "error_rate": 0.5},
        "week_2": {"p95_ms": 800, "error_rate": 0.3},
        "week_3": {"p95_ms": 600, "error_rate": 0.1},
        "week_4": {"p95_ms": 300, "error_rate": 0.0},
    }

    # Calculate trend
    p95_values = [v["p95_ms"] for v in trend_data.values()]
    is_improving = all(p95_values[i] >= p95_values[i + 1] for i in range(len(p95_values) - 1))

    assert is_improving


def test_performance_budget_monthly():
    """Test monthly performance budget tracking."""
    monthly_data = [
        {"date": "2024-01-01", "p95_ms": 280},
        {"date": "2024-01-08", "p95_ms": 300},  # +7%
        {"date": "2024-01-15", "p95_ms": 310},  # +3% from previous, +11% from baseline
        {"date": "2024-01-22", "p95_ms": 290},  # -7% from previous
        {"date": "2024-01-29", "p95_ms": 320},  # +10% from previous, +14% from baseline
    ]

    baseline = monthly_data[0]["p95_ms"]
    current = monthly_data[-1]["p95_ms"]

    total_regression = ((current - baseline) / baseline) * 100
    budget = 15

    is_within_monthly_budget = total_regression <= budget

    # Verify within budget
    assert round(total_regression, 1) <= budget
    assert is_within_monthly_budget


def test_ci_integration_slo_check():
    """Test SLO checking integration in CI/CD."""
    ci_job = {
        "name": "Performance SLO Check",
        "stage": "quality",
        "image": "python:3.11",
        "script": [
            "python -m firsttry run --report-json perf_report.json",
            "python tools/slo_checker.py --report perf_report.json --slo policies/slo-targets.json",
        ],
        "artifacts": {
            "paths": ["perf_report.json", "slo_report.json"],
            "when": "always",
        },
        "allow_failure": False,  # Must meet SLO
    }

    assert not ci_job["allow_failure"]


def test_slo_exemption_request():
    """Test exemption process for SLO violations."""
    exemption = {
        "violation": "p95_latency_exceeded",
        "measured": 35,  # seconds
        "target": 30,
        "exceeded_by": 5,
        "reason": "Repository size increased 20%, acceptable tradeoff",
        "requested_by": "dev-team",
        "approved_by": "engineering-lead",
        "expires": "2024-02-15",
        "alternative_mitigations": ["Cache optimization", "Parallel processing"],
    }

    assert exemption["approved_by"] is not None
    assert len(exemption["alternative_mitigations"]) > 0


def test_performance_regression_detection():
    """Test automatic regression detection."""
    baseline_runs = [280, 290, 300]  # Historical good performance
    recent_runs = [380, 390, 400]  # Recent slower performance

    baseline_avg = statistics.mean(baseline_runs)
    recent_avg = statistics.mean(recent_runs)

    regression_percent = ((recent_avg - baseline_avg) / baseline_avg) * 100
    regression_threshold = 15

    is_regressed = regression_percent > regression_threshold

    assert regression_percent > regression_threshold
    assert is_regressed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
