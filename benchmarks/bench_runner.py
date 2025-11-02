#!/usr/bin/env python3
"""
FirstTry Benchmark Runner

Runs comprehensive benchmarks to answer the 5 key performance questions:
1. Startup cost (--help, --version)
2. Cold run performance 
3. Warm run + cache effectiveness
4. Profile/tier overhead
5. CI parity cost

Author: FirstTry Engineering
Date: November 2, 2025
"""

import subprocess
import time
import json
import os
import shlex
import platform
import pathlib
import datetime
import sys
import re
import shutil
from typing import Dict, List, Any, Optional

ROOT = pathlib.Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "benchmarks" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

class BenchmarkRunner:
    def __init__(self, config_path: pathlib.Path):
        self.config_path = config_path
        self.config = self._load_config()
        self.results = []
        
    def _load_config(self) -> Dict[str, Any]:
        """Load benchmark configuration"""
        try:
            import yaml
        except ImportError:
            print("❌ YAML library not found. Install with: pip install pyyaml")
            sys.exit(1)
            
        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    
    def run_cmd(self, cmd: str, cwd: pathlib.Path, cache_state: str = "unknown") -> Dict[str, Any]:
        """Run a command and collect comprehensive metrics"""
        
        # Clear cache if specified
        if cache_state == "cold":
            self._clear_cache(cwd)
        elif cache_state == "warm":
            # Ensure cache exists by running a quick detection
            self._warm_cache(cwd)
            
        # Record start time
        started = time.monotonic()
        
        # Run the command
        proc = subprocess.Popen(
            shlex.split(cmd),
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        output, _ = proc.communicate()
        
        # Record end time
        ended = time.monotonic()
        duration = round(ended - started, 3)
        
        # Extract phase breakdown if present
        phase_breakdown = self._extract_phase_breakdown(output)
        
        # Detect environment
        environment = self._detect_environment()
        
        # Detect license state
        license_state = self._detect_license_state(output)
        
        return {
            "cmd": cmd,
            "cwd": str(cwd),
            "total_time_sec": duration,
            "exit_code": proc.returncode,
            "output": output,
            "cache_state": cache_state,
            "phase_breakdown": phase_breakdown,
            "cpu_count": os.cpu_count(),
            "repo_size_files": self._count_files(cwd),
            "firsttry_version": self._detect_firsttry_version(),
            "environment": environment,
            "license_state": license_state,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        }
    
    def _clear_cache(self, repo_path: pathlib.Path):
        """Clear FirstTry cache for cold runs"""
        cache_path = repo_path / ".firsttry" / "cache"
        if cache_path.exists():
            shutil.rmtree(cache_path)
            print(f"🗑️  Cleared cache for {repo_path.name}")
    
    def _warm_cache(self, repo_path: pathlib.Path):
        """Ensure cache is warmed up for warm runs"""
        # Run a quick detection to populate cache
        try:
            subprocess.run(
                ["python", "-m", "firsttry", "run", "--source", "detect", "--quiet"],
                cwd=repo_path,
                capture_output=True,
                timeout=60
            )
        except subprocess.TimeoutExpired:
            print(f"⚠️  Cache warming timed out for {repo_path.name}")
        except Exception:
            pass  # Cache warming is best-effort
    
    def _extract_phase_breakdown(self, output: str) -> Optional[Dict[str, float]]:
        """Extract timing phases from FirstTry output"""
        if "Time split" not in output:
            return None
            
        # Look for phase timing patterns
        phases = {}
        for line in output.split('\n'):
            if 'fast:' in line and 's' in line:
                match = re.search(r'fast:\s*([\d.]+)s', line)
                if match:
                    phases['fast'] = float(match.group(1))
            elif 'normal:' in line and 's' in line:
                match = re.search(r'normal:\s*([\d.]+)s', line)
                if match:
                    phases['normal'] = float(match.group(1))
            elif 'slow:' in line and 's' in line:
                match = re.search(r'slow:\s*([\d.]+)s', line)
                if match:
                    phases['slow'] = float(match.group(1))
        
        return phases if phases else None
    
    def _detect_firsttry_version(self) -> str:
        """Detect FirstTry version"""
        try:
            result = subprocess.run(
                ["python", "-m", "firsttry", "--version"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                match = re.search(r"firsttry\s+([\d\.]+)", result.stdout)
                return match.group(1) if match else "unknown"
        except Exception:
            pass
        return "unknown"
    
    def _detect_environment(self) -> str:
        """Detect execution environment"""
        if os.path.exists("/.dockerenv"):
            return "devcontainer"
        elif os.environ.get("CODESPACES"):
            return "codespace"
        else:
            return "local"
    
    def _detect_license_state(self, output: str) -> str:
        """Detect license state from command output"""
        if "license" in output.lower():
            if "trial" in output.lower():
                return "trial"
            elif "locked" in output.lower():
                return "locked"
        return "not-required"
    
    def _count_files(self, path: pathlib.Path) -> int:
        """Count files in repository"""
        total = 0
        try:
            for root, dirs, files in os.walk(path):
                # Skip common ignored directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__']]
                total += len(files)
        except Exception:
            return 0
        return total
    
    def run_benchmark_suite(self) -> Dict[str, Any]:
        """Run the complete benchmark suite"""
        print("🏁 Starting FirstTry Benchmark Suite")
        print(f"📂 Root: {ROOT}")
        print(f"🖥️  Host: {platform.platform()}")
        print(f"🐍 Python: {platform.python_version()}")
        print(f"⚡ CPUs: {os.cpu_count()}")
        print()
        
        all_results = {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "host": {
                "platform": platform.platform(),
                "python": platform.python_version(),
                "cpus": os.cpu_count(),
            },
            "firsttry_version": self._detect_firsttry_version(),
            "environment": self._detect_environment(),
            "config": self.config,
            "results": [],
            "summary": {},
        }
        
        # Track results by question for analysis
        question_results = {
            "startup-cost": [],
            "cold-run": [],
            "warm-run": [],
            "profile-cost": [],
            "ci-parity-cost": []
        }
        
        # Run benchmarks for each repo
        for repo in self.config["repos"]:
            repo_path = ROOT / repo["path"]
            
            if not repo_path.exists():
                print(f"⚠️  Skipping {repo['id']}: {repo_path} does not exist")
                continue
                
            print(f"🔥 Benchmarking {repo['id']}: {repo.get('description', 'No description')}")
            repo_files = self._count_files(repo_path)
            print(f"📁 Files: {repo_files}")
            
            for cmd_spec in repo["commands"]:
                cmd = cmd_spec["cmd"]
                cache_state = cmd_spec.get("cache", "unknown")
                question = cmd_spec.get("question", "unknown")
                
                print(f"  🧪 {cmd_spec['name']}: {cmd}")
                
                # Run the command
                result = self.run_cmd(cmd, repo_path, cache_state)
                result["repo_id"] = repo["id"]
                result["repo_files"] = repo_files
                result["command_name"] = cmd_spec["name"]
                result["question"] = question
                
                # Add to results
                all_results["results"].append(result)
                if question in question_results:
                    question_results[question].append(result)
                
                # Console feedback
                status = "✅" if result["exit_code"] == 0 else "❌"
                print(f"     {status} {result['total_time_sec']}s (exit {result['exit_code']})")
            
            print()
        
        # Generate pass/fail analysis
        validation_results = self._validate_performance(all_results["results"])
        all_results["validation"] = validation_results
        
        # Generate summary by question
        all_results["summary"] = self._generate_summary(question_results)
        
        return all_results
    
    def _validate_performance(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply pass/fail rules to benchmark results"""
        targets = self.config.get("targets", {})
        validation = {
            "overall_pass": True,
            "checks": [],
            "warnings": [],
            "failures": []
        }
        
        for result in results:
            cmd = result["cmd"]
            duration = result["total_time_sec"]
            question = result.get("question", "unknown")
            
            # Startup cost validation
            if question == "startup-cost":
                if duration <= targets.get("startup_max_sec", 0.5):
                    validation["checks"].append(f"✅ PASS: {cmd} startup ({duration}s <= 0.5s)")
                elif duration <= targets.get("startup_warn_sec", 1.0):
                    validation["warnings"].append(f"⚠️ WARN: {cmd} startup ({duration}s > 0.5s)")
                else:
                    validation["failures"].append(f"❌ FAIL: {cmd} startup ({duration}s > 1.0s)")
                    validation["overall_pass"] = False
            
            # Cold run validation
            elif question == "cold-run":
                repo_files = result.get("repo_size_files", 0)
                is_large = repo_files > 5000
                max_time = targets.get("cold_large_max_sec", 60) if is_large else targets.get("cold_small_max_sec", 30)
                warn_time = targets.get("cold_small_warn_sec", 45)
                
                if duration <= max_time:
                    validation["checks"].append(f"✅ PASS: {cmd} cold run ({duration}s <= {max_time}s)")
                elif duration <= warn_time and not is_large:
                    validation["warnings"].append(f"⚠️ WARN: {cmd} cold run ({duration}s > {max_time}s)")
                else:
                    validation["failures"].append(f"❌ FAIL: {cmd} cold run ({duration}s > {max_time}s)")
                    validation["overall_pass"] = False
            
            # Changed-only validation
            elif "changed-only" in cmd or "--changed-only" in cmd:
                max_time = targets.get("changed_only_max_sec", 30)
                if duration <= max_time:
                    validation["checks"].append(f"✅ PASS: {cmd} changed-only ({duration}s <= {max_time}s)")
                else:
                    validation["failures"].append(f"❌ FAIL: {cmd} changed-only ({duration}s > {max_time}s)")
                    validation["overall_pass"] = False
            
            # Strict profile validation  
            elif "--profile strict" in cmd:
                max_time = targets.get("strict_max_sec", 90)
                fail_time = targets.get("strict_fail_sec", 120)
                if duration <= max_time:
                    validation["checks"].append(f"✅ PASS: {cmd} strict profile ({duration}s <= {max_time}s)")
                elif duration <= fail_time:
                    validation["warnings"].append(f"⚠️ WARN: {cmd} strict profile ({duration}s > {max_time}s)")
                else:
                    validation["failures"].append(f"❌ FAIL: {cmd} strict profile ({duration}s > {fail_time}s)")
                    validation["overall_pass"] = False
        
        return validation
    
    def _generate_summary(self, question_results: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Generate summary answering the 5 key questions"""
        summary = {}
        
        # Question 1: Startup cost
        startup_times = [r["total_time_sec"] for r in question_results["startup-cost"]]
        if startup_times:
            summary["startup_cost"] = {
                "avg_time_sec": round(sum(startup_times) / len(startup_times), 3),
                "max_time_sec": max(startup_times),
                "commands_tested": len(startup_times)
            }
        
        # Question 2: Cold run performance
        cold_times = [r["total_time_sec"] for r in question_results["cold-run"]]
        if cold_times:
            summary["cold_run"] = {
                "avg_time_sec": round(sum(cold_times) / len(cold_times), 3),
                "max_time_sec": max(cold_times),
                "commands_tested": len(cold_times)
            }
        
        # Question 3: Warm run effectiveness
        warm_times = [r["total_time_sec"] for r in question_results["warm-run"]]
        if warm_times:
            summary["warm_run"] = {
                "avg_time_sec": round(sum(warm_times) / len(warm_times), 3),
                "max_time_sec": max(warm_times),
                "commands_tested": len(warm_times)
            }
        
        # Question 4: Profile/tier cost
        profile_times = [r["total_time_sec"] for r in question_results["profile-cost"]]
        if profile_times:
            summary["profile_cost"] = {
                "avg_time_sec": round(sum(profile_times) / len(profile_times), 3),
                "max_time_sec": max(profile_times),
                "commands_tested": len(profile_times)
            }
        
        # Question 5: CI parity cost
        ci_times = [r["total_time_sec"] for r in question_results["ci-parity-cost"]]
        if ci_times:
            summary["ci_parity_cost"] = {
                "avg_time_sec": round(sum(ci_times) / len(ci_times), 3),
                "max_time_sec": max(ci_times),
                "commands_tested": len(ci_times)
            }
        
        return summary
    
    def save_results(self, results: Dict[str, Any]) -> pathlib.Path:
        """Save results to timestamped JSON file"""
        timestamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        output_file = RESULTS_DIR / f"{timestamp}.json"
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
            
        return output_file
    
    def print_summary_report(self, results: Dict[str, Any]):
        """Print human-readable summary report"""
        print("\n" + "="*60)
        print("🏆 FIRSTTRY BENCHMARK SUMMARY REPORT")
        print("="*60)
        
        # Overall status
        validation = results.get("validation", {})
        overall_pass = validation.get("overall_pass", False)
        status = "✅ PASS" if overall_pass else "❌ FAIL"
        print(f"\n🎯 Overall Status: {status}")
        
        # Answer the 5 key questions
        summary = results.get("summary", {})
        
        print(f"\n📊 THE 5 KEY QUESTIONS ANSWERED:")
        print("-" * 40)
        
        if "startup_cost" in summary:
            s = summary["startup_cost"]
            print(f"1. 🚀 Startup cost: {s['avg_time_sec']}s avg, {s['max_time_sec']}s max ({s['commands_tested']} tests)")
        
        if "cold_run" in summary:
            s = summary["cold_run"]
            print(f"2. ❄️  Cold run: {s['avg_time_sec']}s avg, {s['max_time_sec']}s max ({s['commands_tested']} tests)")
        
        if "warm_run" in summary:
            s = summary["warm_run"]
            print(f"3. 🔥 Warm run: {s['avg_time_sec']}s avg, {s['max_time_sec']}s max ({s['commands_tested']} tests)")
        
        if "profile_cost" in summary:
            s = summary["profile_cost"]
            print(f"4. ⚖️  Profile cost: {s['avg_time_sec']}s avg, {s['max_time_sec']}s max ({s['commands_tested']} tests)")
        
        if "ci_parity_cost" in summary:
            s = summary["ci_parity_cost"]
            print(f"5. 🔄 CI parity: {s['avg_time_sec']}s avg, {s['max_time_sec']}s max ({s['commands_tested']} tests)")
        
        # Validation details
        print(f"\n✅ PASSES ({len(validation.get('checks', []))})")
        for check in validation.get('checks', [])[:5]:  # Show first 5
            print(f"  {check}")
        if len(validation.get('checks', [])) > 5:
            print(f"  ... and {len(validation.get('checks', [])) - 5} more")
        
        if validation.get('warnings'):
            print(f"\n⚠️  WARNINGS ({len(validation.get('warnings', []))})")
            for warning in validation.get('warnings', []):
                print(f"  {warning}")
        
        if validation.get('failures'):
            print(f"\n❌ FAILURES ({len(validation.get('failures', []))})")
            for failure in validation.get('failures', []):
                print(f"  {failure}")
        
        print(f"\n📄 Full results: {len(results.get('results', []))} commands across {len(self.config.get('repos', []))} repos")


def main():
    """Main benchmark entry point"""
    config_path = ROOT / "benchmarks" / "bench_config.yaml"
    
    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        sys.exit(1)
    
    # Create and run benchmark
    runner = BenchmarkRunner(config_path)
    results = runner.run_benchmark_suite()
    
    # Save results
    output_file = runner.save_results(results)
    print(f"💾 Results saved: {output_file}")
    
    # Print summary
    runner.print_summary_report(results)
    
    # Exit with appropriate code
    overall_pass = results.get("validation", {}).get("overall_pass", False)
    sys.exit(0 if overall_pass else 1)


if __name__ == "__main__":
    main()