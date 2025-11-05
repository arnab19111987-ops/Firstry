from __future__ import annotations
import json
import time
import statistics
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

from .cached_orchestrator import run_checks_for_profile
from .run_profiles import select_checks


@dataclass
class BenchmarkResult:
    """Single benchmark run result"""

    scenario: str
    profile: str
    duration: float
    checks_run: int
    checks_passed: int
    checks_failed: int
    checks_skipped: int
    cache_hits: int
    timestamp: str
    optimizations_used: List[str]
    memory_peak_mb: Optional[float] = None


@dataclass
class PerformanceMetrics:
    """Aggregated performance metrics"""

    scenario: str
    baseline_time: float
    optimized_time: float
    improvement_factor: float
    improvement_percentage: float
    time_saved_seconds: float
    samples: int
    confidence_interval: tuple[float, float]


class PerformanceBenchmark:
    """Comprehensive performance benchmarking system"""

    def __init__(self, repo_root: str):
        self.repo_root = repo_root
        self.results: List[BenchmarkResult] = []
        self.metrics_history: List[PerformanceMetrics] = []

    def add_result(self, result: BenchmarkResult):
        """Add a benchmark result"""
        self.results.append(result)

    async def benchmark_scenario(
        self,
        scenario: str,
        profile: str,
        checks: List[str],
        use_cache: bool = True,
        changed_files: Optional[List[str]] = None,
        runs: int = 3,
    ) -> List[BenchmarkResult]:
        """Benchmark a specific scenario multiple times"""

        scenario_results = []
        optimizations = []

        if use_cache:
            optimizations.append("caching")
        if changed_files:
            optimizations.append("change-detection")
        if profile in ["fast", "dev"]:
            optimizations.append("profile-selection")

        for run in range(runs):
            print(f"  Run {run + 1}/{runs}...")

            start_time = time.time()

            try:
                result = await run_checks_for_profile(
                    repo_root=self.repo_root,
                    checks=checks,
                    use_cache=use_cache,
                    changed_files=changed_files,
                    profile=profile,
                )

                duration = time.time() - start_time

                # Analyze results
                checks_passed = sum(
                    1 for r in result.values() if r.get("status") == "ok"
                )
                checks_failed = sum(
                    1 for r in result.values() if r.get("status") == "fail"
                )
                checks_skipped = sum(
                    1 for r in result.values() if r.get("status") == "skipped"
                )
                cache_hits = sum(1 for r in result.values() if r.get("cached", False))

                benchmark_result = BenchmarkResult(
                    scenario=scenario,
                    profile=profile,
                    duration=duration,
                    checks_run=len(checks),
                    checks_passed=checks_passed,
                    checks_failed=checks_failed,
                    checks_skipped=checks_skipped,
                    cache_hits=cache_hits,
                    timestamp=datetime.now().isoformat(),
                    optimizations_used=optimizations.copy(),
                )

                scenario_results.append(benchmark_result)
                self.add_result(benchmark_result)

            except Exception as e:
                print(f"    ❌ Run failed: {e}")
                # Add failed run with max duration
                failed_result = BenchmarkResult(
                    scenario=f"{scenario} (failed)",
                    profile=profile,
                    duration=300.0,  # Penalty time
                    checks_run=len(checks),
                    checks_passed=0,
                    checks_failed=len(checks),
                    checks_skipped=0,
                    cache_hits=0,
                    timestamp=datetime.now().isoformat(),
                    optimizations_used=optimizations.copy(),
                )
                scenario_results.append(failed_result)
                self.add_result(failed_result)

        return scenario_results

    def calculate_metrics(
        self,
        baseline_results: List[BenchmarkResult],
        optimized_results: List[BenchmarkResult],
        scenario: str,
    ) -> PerformanceMetrics:
        """Calculate performance improvement metrics"""

        baseline_times = [r.duration for r in baseline_results]
        optimized_times = [r.duration for r in optimized_results]

        baseline_avg = statistics.mean(baseline_times)
        optimized_avg = statistics.mean(optimized_times)

        improvement_factor = (
            baseline_avg / optimized_avg if optimized_avg > 0 else float("inf")
        )
        improvement_percentage = ((baseline_avg - optimized_avg) / baseline_avg) * 100
        time_saved = baseline_avg - optimized_avg

        # Simple confidence interval (mean ± 1.96 * std_err)
        try:
            std_err = statistics.stdev(optimized_times) / len(optimized_times) ** 0.5
            confidence_interval = (
                optimized_avg - 1.96 * std_err,
                optimized_avg + 1.96 * std_err,
            )
        except statistics.StatisticsError:
            confidence_interval = (optimized_avg, optimized_avg)

        return PerformanceMetrics(
            scenario=scenario,
            baseline_time=baseline_avg,
            optimized_time=optimized_avg,
            improvement_factor=improvement_factor,
            improvement_percentage=improvement_percentage,
            time_saved_seconds=time_saved,
            samples=len(optimized_results),
            confidence_interval=confidence_interval,
        )

    def export_results(self, output_path: Path):
        """Export benchmark results to JSON"""

        export_data = {
            "benchmark_info": {
                "repo_root": self.repo_root,
                "timestamp": datetime.now().isoformat(),
                "total_scenarios": len(set(r.scenario for r in self.results)),
                "total_runs": len(self.results),
            },
            "results": [asdict(r) for r in self.results],
            "metrics": [asdict(m) for m in self.metrics_history],
        }

        with open(output_path, "w") as f:
            json.dump(export_data, f, indent=2)

        print(f"📊 Benchmark results exported to: {output_path}")

    def print_summary(self):
        """Print benchmark summary"""

        print("\n📈 Performance Benchmark Summary")
        print("=" * 50)

        scenarios = set(r.scenario for r in self.results)

        for scenario in sorted(scenarios):
            scenario_results = [r for r in self.results if r.scenario == scenario]
            if not scenario_results:
                continue

            avg_duration = statistics.mean(r.duration for r in scenario_results)
            min_duration = min(r.duration for r in scenario_results)
            max_duration = max(r.duration for r in scenario_results)

            print(f"\n🎯 {scenario}:")
            print(f"   • Runs: {len(scenario_results)}")
            print(f"   • Average: {avg_duration:.2f}s")
            print(f"   • Range: {min_duration:.2f}s - {max_duration:.2f}s")

            # Show optimization impact
            optimizations = scenario_results[0].optimizations_used
            if optimizations:
                print(f"   • Optimizations: {', '.join(optimizations)}")

        # Overall statistics
        if self.metrics_history:
            print("\n🏆 Performance Improvements:")
            for metrics in self.metrics_history:
                print(f"   • {metrics.scenario}:")
                print(f"     - {metrics.improvement_factor:.1f}x faster")
                print(f"     - {metrics.improvement_percentage:.1f}% improvement")
                print(f"     - {metrics.time_saved_seconds:.1f}s saved")


async def run_comprehensive_benchmark(repo_root: str) -> PerformanceBenchmark:
    """Run comprehensive performance benchmarks"""

    print("🚀 FirstTry Performance Validation Suite")
    print("=" * 50)

    benchmark = PerformanceBenchmark(repo_root)

    # Define benchmark scenarios
    scenarios = [
        {
            "name": "Full Suite (Baseline)",
            "profile": "strict",
            "use_cache": False,
            "changed_files": None,
            "description": "Original performance baseline - no optimizations",
        },
        {
            "name": "Full Suite (Optimized)",
            "profile": "strict",
            "use_cache": True,
            "changed_files": None,
            "description": "All optimizations enabled",
        },
        {
            "name": "Incremental (Python Changes)",
            "profile": "dev",
            "use_cache": True,
            "changed_files": ["src/firsttry/cli.py", "src/firsttry/cache.py"],
            "description": "Typical development scenario - Python files changed",
        },
        {
            "name": "Incremental (Doc Changes)",
            "profile": "fast",
            "use_cache": True,
            "changed_files": ["README.md", "docs/api.md"],
            "description": "Documentation-only changes",
        },
        {
            "name": "Cache Hit Scenario",
            "profile": "dev",
            "use_cache": True,
            "changed_files": None,
            "description": "Second run with full cache hits",
        },
    ]

    results_by_scenario = {}

    for scenario in scenarios:
        print(f"\n🎯 Benchmarking: {scenario['name']}")
        print(f"   {scenario['description']}")

        # Get checks for the profile
        checks = select_checks(scenario["profile"])

        # Run benchmark
        scenario_results = await benchmark.benchmark_scenario(
            scenario=scenario["name"],
            profile=scenario["profile"],
            checks=checks,
            use_cache=scenario["use_cache"],
            changed_files=scenario["changed_files"],
            runs=3,
        )

        results_by_scenario[scenario["name"]] = scenario_results

        # Show immediate results
        durations = [r.duration for r in scenario_results]
        avg_duration = statistics.mean(durations)
        print(f"   ✅ Average: {avg_duration:.2f}s")

    # Calculate improvement metrics
    print("\n📊 Calculating Performance Improvements...")

    # Compare optimized vs baseline
    if (
        "Full Suite (Baseline)" in results_by_scenario
        and "Full Suite (Optimized)" in results_by_scenario
    ):
        metrics = benchmark.calculate_metrics(
            baseline_results=results_by_scenario["Full Suite (Baseline)"],
            optimized_results=results_by_scenario["Full Suite (Optimized)"],
            scenario="Full Suite Optimization",
        )
        benchmark.metrics_history.append(metrics)

    # Compare incremental scenarios
    if (
        "Full Suite (Optimized)" in results_by_scenario
        and "Incremental (Python Changes)" in results_by_scenario
    ):
        metrics = benchmark.calculate_metrics(
            baseline_results=results_by_scenario["Full Suite (Optimized)"],
            optimized_results=results_by_scenario["Incremental (Python Changes)"],
            scenario="Incremental Development",
        )
        benchmark.metrics_history.append(metrics)

    return benchmark


def create_test_project(base_dir: Path) -> Path:
    """Create a test project for benchmarking"""

    test_project = base_dir / "benchmark_test_project"
    test_project.mkdir(exist_ok=True)

    # Create pyproject.toml
    (test_project / "pyproject.toml").write_text(
        """
[build-system]
requires = ["setuptools>=45", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "benchmark-test"
version = "0.1.0"
description = "Test project for FirstTry benchmarks"

[tool.ruff]
select = ["E", "F", "W", "I"]
line-length = 88

[tool.mypy]
python_version = "3.10"
strict = true
"""
    )

    # Create source structure
    src_dir = test_project / "src" / "benchmark_test"
    src_dir.mkdir(parents=True)

    (src_dir / "__init__.py").write_text('"""Benchmark test package"""')

    # Create some Python modules
    (src_dir / "core.py").write_text(
        """
\"\"\"Core functionality for benchmark testing\"\"\"
from typing import List, Dict, Any
import json


class DataProcessor:
    \"\"\"Process various data formats\"\"\"
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.cache: Dict[str, Any] = {}
    
    def process_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        \"\"\"Process a list of data items\"\"\"
        results = []
        
        for item in data:
            processed = self._process_item(item)
            if processed:
                results.append(processed)
        
        return results
    
    def _process_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        \"\"\"Process a single data item\"\"\"
        if not isinstance(item, dict):
            return {}
        
        # Apply transformations based on config
        result = item.copy()
        
        for key, value in self.config.items():
            if key in result:
                result[key] = self._transform_value(result[key], value)
        
        return result
    
    def _transform_value(self, value: Any, transform_config: Any) -> Any:
        \"\"\"Transform a value based on configuration\"\"\"
        if isinstance(transform_config, str):
            if transform_config == "upper":
                return str(value).upper()
            elif transform_config == "lower":
                return str(value).lower()
        
        return value
"""
    )

    # Create test files
    tests_dir = test_project / "tests"
    tests_dir.mkdir()

    (tests_dir / "__init__.py").write_text("")

    (tests_dir / "test_core.py").write_text(
        """
\"\"\"Tests for core functionality\"\"\"
import pytest
from benchmark_test.core import DataProcessor


class TestDataProcessor:
    \"\"\"Test the DataProcessor class\"\"\"
    
    def test_init(self):
        \"\"\"Test processor initialization\"\"\"
        config = {"name": "upper"}
        processor = DataProcessor(config)
        assert processor.config == config
        assert processor.cache == {}
    
    def test_process_data_empty(self):
        \"\"\"Test processing empty data\"\"\"
        processor = DataProcessor({})
        result = processor.process_data([])
        assert result == []
    
    def test_process_data_single_item(self):
        \"\"\"Test processing single item\"\"\"
        config = {"name": "upper"}
        processor = DataProcessor(config)
        
        data = [{"name": "test", "value": 42}]
        result = processor.process_data(data)
        
        assert len(result) == 1
        assert result[0]["name"] == "TEST"
        assert result[0]["value"] == 42
    
    def test_process_data_multiple_items(self):
        \"\"\"Test processing multiple items\"\"\"
        config = {"name": "upper", "description": "lower"}
        processor = DataProcessor(config)
        
        data = [
            {"name": "First", "description": "FIRST ITEM"},
            {"name": "Second", "description": "SECOND ITEM"}
        ]
        result = processor.process_data(data)
        
        assert len(result) == 2
        assert result[0]["name"] == "FIRST"
        assert result[0]["description"] == "first item"
        assert result[1]["name"] == "SECOND"
        assert result[1]["description"] == "second item"
    
    @pytest.mark.parametrize("transform,input_val,expected", [
        ("upper", "hello", "HELLO"),
        ("lower", "WORLD", "world"),
        ("invalid", "test", "test"),
    ])
    def test_transform_value(self, transform, input_val, expected):
        \"\"\"Test value transformation\"\"\"
        processor = DataProcessor({})
        result = processor._transform_value(input_val, transform)
        assert result == expected
"""
    )

    # Create more test files to make it substantial
    for i in range(5):
        (tests_dir / f"test_module_{i}.py").write_text(
            f"""
\"\"\"Test module {i}\"\"\"
import pytest


def test_simple_{i}():
    \"\"\"Simple test {i}\"\"\"
    assert {i} == {i}


def test_addition_{i}():
    \"\"\"Test addition for module {i}\"\"\"
    assert {i} + 1 == {i + 1}


class TestClass{i}:
    \"\"\"Test class {i}\"\"\"
    
    def test_method_a(self):
        \"\"\"Test method A\"\"\"
        assert True
    
    def test_method_b(self):
        \"\"\"Test method B\"\"\"
        assert not False
    
    @pytest.mark.parametrize("value", [1, 2, 3, 4, 5])
    def test_parametrized(self, value):
        \"\"\"Parametrized test\"\"\"
        assert value > 0
"""
        )

    return test_project


async def validate_performance_targets(
    benchmark: PerformanceBenchmark,
) -> Dict[str, bool]:
    """Validate that performance targets are met"""

    print("\n🎯 Performance Target Validation")
    print("=" * 40)

    targets = {
        "sub_60s_optimized": False,
        "2x_improvement": False,
        "incremental_sub_30s": False,
        "cache_hit_sub_10s": False,
    }

    # Check each target
    for metrics in benchmark.metrics_history:
        if "Full Suite" in metrics.scenario:
            # Target: Optimized full suite under 60s
            if metrics.optimized_time < 60:
                targets["sub_60s_optimized"] = True
                print(f"✅ Sub-60s target: {metrics.optimized_time:.1f}s")
            else:
                print(f"❌ Sub-60s target: {metrics.optimized_time:.1f}s (missed)")

            # Target: 2x improvement
            if metrics.improvement_factor >= 2.0:
                targets["2x_improvement"] = True
                print(f"✅ 2x improvement: {metrics.improvement_factor:.1f}x")
            else:
                print(f"❌ 2x improvement: {metrics.improvement_factor:.1f}x (missed)")

        elif "Incremental" in metrics.scenario:
            # Target: Incremental development under 30s
            if metrics.optimized_time < 30:
                targets["incremental_sub_30s"] = True
                print(f"✅ Incremental sub-30s: {metrics.optimized_time:.1f}s")
            else:
                print(f"❌ Incremental sub-30s: {metrics.optimized_time:.1f}s (missed)")

    # Check cache hit performance
    cache_results = [r for r in benchmark.results if "Cache Hit" in r.scenario]
    if cache_results:
        avg_cache_time = sum(r.duration for r in cache_results) / len(cache_results)
        if avg_cache_time < 10:
            targets["cache_hit_sub_10s"] = True
            print(f"✅ Cache hit sub-10s: {avg_cache_time:.1f}s")
        else:
            print(f"❌ Cache hit sub-10s: {avg_cache_time:.1f}s (missed)")

    # Overall assessment
    passed = sum(targets.values())
    total = len(targets)

    print(f"\n🏆 Performance Assessment: {passed}/{total} targets met")

    if passed == total:
        print("🎉 All performance targets achieved!")
    elif passed >= total * 0.75:
        print("⚡ Good performance - most targets met")
    else:
        print("⚠️  Performance needs improvement")

    return targets
