#!/usr/bin/env python3
"""
FirstTry Benchmark Harness - Repo-Agnostic Cold/Warm Performance Runner

Executes cold (no cache) and warm (with cache) benchmark runs of FirstTry CLI,
captures comprehensive environment & performance telemetry, and emits both
human-readable Markdown and machine-parseable JSON for CI/CD integration.

Usage:
    python ft_bench_harness.py [--tier lite|pro] [--mode fast|full]
                               [--max-procs N] [--timeout-s S]
                               [--no-telemetry] [--regress-pct PCT]
                               [--skip-cold] [--skip-warm]

Exit codes:
    0 = Success
    4 = Regression threshold exceeded
    5 = Setup error (invalid args, env issues, etc)
"""

import argparse
import datetime
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

__version__ = "1.0.0"


class BenchRunner:
    """Orchestrate cold/warm benchmark runs with environment capture."""

    def __init__(
        self,
        tier: str = "lite",
        mode: str = "fast",
        max_procs: Optional[int] = None,
        timeout_s: int = 300,
        no_telemetry: bool = True,
        regress_pct: float = 25.0,
        skip_cold: bool = False,
        skip_warm: bool = False,
    ):
        self.tier = tier
        self.mode = mode
        self.max_procs = max_procs or self._auto_procs()
        self.timeout_s = timeout_s
        self.no_telemetry = no_telemetry
        self.regress_pct = regress_pct
        self.skip_cold = skip_cold
        self.skip_warm = skip_warm

        # Setup directories
        self.repo_root = Path.cwd()
        self.bench_dir = self.repo_root / ".firsttry"
        self.artifacts_dir = self.bench_dir / "bench_artifacts"
        self.proof_json = self.bench_dir / "bench_proof.json"
        self.proof_md = self.bench_dir / "bench_proof.md"

        # Ensure directories exist
        self.bench_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        # Placeholder for collected data
        self.data: Dict[str, Any] = {}

    @staticmethod
    def _auto_procs() -> int:
        """Auto-detect CPU core count, capped at 8."""
        cores = os.cpu_count() or 1
        return min(cores, 8)

    def run(self) -> int:
        """Execute benchmark and generate reports. Returns exit code."""
        try:
            # Capture environment snapshot
            self._capture_environment()

            # Compute repo fingerprint
            self._compute_repo_fingerprint()

            # Prepare normalized environment
            env = self._prepare_env()

            # Run cold benchmark (if not skipped)
            if not self.skip_cold:
                self._run_benchmark("cold", env, clear_cache=True)
            else:
                self.data["runs"]["cold"] = {"skipped": True}

            # Run warm benchmark (if not skipped)
            if not self.skip_warm:
                self._run_benchmark("warm", env, clear_cache=False)
            else:
                self.data["runs"]["warm"] = {"skipped": True}

            # Collect cache stats (after warm run for accuracy)
            self._collect_cache_stats()

            # Check regression
            regression = self._check_regression()

            # Generate reports
            self._write_json()
            self._write_markdown()

            # Print markdown to stdout
            print((self.proof_md).read_text())

            return 4 if regression else 0

        except Exception as e:
            print(f"❌ Setup error: {e}", file=sys.stderr)
            return 5

    def _capture_environment(self) -> None:
        """Capture system and tooling environment snapshot."""
        self.data["timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"
        self.data["schema"] = 1

        # Host information
        self.data["host"] = {
            "os": platform.system(),
            "kernel": platform.release(),
            "arch": platform.machine(),
            "cpu_cores": os.cpu_count() or 1,
            "cpu_threads": os.cpu_count() or 1,  # Simplified; threads ≈ cores on most systems
            "total_ram_gb": self._get_total_ram(),
            "disk_free_gb": self._get_disk_free(),
        }

        # Python & venv
        self.data["python"] = {
            "version": platform.python_version(),
            "executable": sys.executable,
            "venv_active": hasattr(sys, "real_prefix")
            or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix),
        }

        # FirstTry version
        ft_version = self._run_cmd(
            [sys.executable, "-m", "firsttry", "--version"],
            timeout=10,
        )
        self.data["firsttry"] = {
            "version": ft_version.strip() if ft_version else "unknown",
            "tier": self.tier,
            "mode": self.mode,
        }

        # External tools
        self.data["tooling"] = {
            "node": self._get_tool_version(["node", "--version"]),
            "npm": self._get_tool_version(["npm", "--version"]),
            "ruff": self._get_tool_version(["ruff", "--version"]),
            "pytest": self._get_tool_version(["pytest", "--version"]),
            "mypy": self._get_tool_version(["mypy", "--version"]),
            "bandit": self._get_tool_version(["bandit", "--version"]),
        }

        # Git info (if in repo)
        self.data["git"] = self._get_git_info()

        # Environment configuration
        self.data["env"] = {
            "FT_MAX_PROCS": self.max_procs,
            "FT_TIMEOUT_S": self.timeout_s,
            "FT_SEND_TELEMETRY": 0 if self.no_telemetry else 1,
        }

        # Runs placeholder
        self.data["runs"] = {}

    def _compute_repo_fingerprint(self) -> None:
        """Compute repo fingerprint: file count, size, hash."""
        file_count = 0
        total_bytes = 0
        ext_count: Dict[str, int] = {}
        mtime_sum = 0

        # Walk repo excluding common non-essential paths
        exclude = {
            ".git",
            ".venv_tmp",
            ".venv",
            "__pycache__",
            "node_modules",
            ".firsttry",
            ".pytest_cache",
            ".mypy_cache",
            "dist",
            "build",
            ".eggs",
            "*.egg-info",
        }

        for root, dirs, files in os.walk(self.repo_root):
            # Prune excluded directories
            dirs[:] = [d for d in dirs if d not in exclude]

            for fname in files:
                fpath = Path(root) / fname
                try:
                    stat = fpath.stat()
                    file_count += 1
                    total_bytes += stat.st_size
                    ext = fpath.suffix or ".no_ext"
                    ext_count[ext] = ext_count.get(ext, 0) + 1
                    mtime_sum += int(stat.st_mtime)
                except (OSError, PermissionError):
                    pass

        # Top 8 extensions
        top_exts = sorted(ext_count.items(), key=lambda x: x[1], reverse=True)[:8]

        # Compute a simple content-agnostic hash using filenames/sizes/mtimes
        hash_input = f"{file_count}:{total_bytes}:{mtime_sum}".encode("utf-8")
        fingerprint_hash = hashlib.sha1(hash_input).hexdigest()[:16]

        self.data["repo"] = {
            "file_count": file_count,
            "total_bytes": total_bytes,
            "total_gb": round(total_bytes / (1024**3), 3),
            "top_extensions": [{"ext": ext, "count": count} for ext, count in top_exts],
            "fingerprint_hash": fingerprint_hash,
        }

    def _prepare_env(self) -> Dict[str, str]:
        """Prepare normalized environment for benchmark runs."""
        env = os.environ.copy()
        env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        env["FT_MAX_PROCS"] = str(self.max_procs)
        env["FT_TIMEOUT_S"] = str(self.timeout_s)
        env["FT_SEND_TELEMETRY"] = "0" if self.no_telemetry else "1"
        return env

    def _run_benchmark(self, run_type: str, env: Dict[str, str], clear_cache: bool) -> None:
        """Execute a single benchmark run (cold or warm)."""
        if clear_cache:
            cache_dir = self.bench_dir / "cache"
            if cache_dir.exists():
                shutil.rmtree(cache_dir)

        # Build command
        cmd = [
            sys.executable,
            "-m",
            "firsttry",
            "run",
            self.mode,
            "--tier",
            self.tier,
            "--show-report",
        ]

        if clear_cache:
            cmd.append("--no-remote-cache")

        log_path = self.artifacts_dir / f"{run_type}.log"

        # Run with timing
        start_time = time.time()
        result_dict, elapsed_s = self._run_cmd_with_timing(
            cmd, env=env, timeout=self.timeout_s, log_file=log_path
        )
        elapsed_s = time.time() - start_time

        # Store result
        self.data["runs"][run_type] = {
            "ok": result_dict["returncode"] == 0,
            "elapsed_s": round(elapsed_s, 2),
            "exit_code": result_dict["returncode"],
            "log": f"bench_artifacts/{run_type}.log",
        }

    def _collect_cache_stats(self) -> None:
        """Collect cache directory statistics."""
        cache_dir = self.bench_dir / "cache"
        cache_bytes = 0
        cache_files = 0

        if cache_dir.exists():
            for root, dirs, files in os.walk(cache_dir):
                for fname in files:
                    fpath = Path(root) / fname
                    try:
                        cache_bytes += fpath.stat().st_size
                        cache_files += 1
                    except (OSError, PermissionError):
                        pass

        # Store in both cold and warm runs
        for run_type in ["cold", "warm"]:
            if run_type in self.data["runs"] and not self.data["runs"][run_type].get("skipped"):
                self.data["runs"][run_type]["cache_bytes"] = cache_bytes
                self.data["runs"][run_type]["cache_files"] = cache_files
                self.data["runs"][run_type]["cache_gb"] = round(cache_bytes / (1024**3), 3)

    def _check_regression(self) -> bool:
        """Check if warm run regressed vs prior baseline. Returns True if regressed."""
        if self.proof_json.exists() and not self.skip_warm:
            try:
                prior_data = json.loads(self.proof_json.read_text())
                prior_warm_elapsed = prior_data.get("runs", {}).get("warm", {}).get("elapsed_s")
                current_warm_elapsed = self.data.get("runs", {}).get("warm", {}).get("elapsed_s")

                if prior_warm_elapsed is not None and current_warm_elapsed is not None:
                    pct_change = (
                        (current_warm_elapsed - prior_warm_elapsed) / prior_warm_elapsed * 100
                    )
                    self.data["regression"] = {
                        "detected": pct_change > self.regress_pct,
                        "prior_warm_s": prior_warm_elapsed,
                        "current_warm_s": current_warm_elapsed,
                        "pct_change": round(pct_change, 1),
                        "threshold_pct": self.regress_pct,
                    }
                    return pct_change > self.regress_pct
            except (json.JSONDecodeError, KeyError, TypeError):
                pass

        self.data["regression"] = {"detected": False}
        return False

    def _write_json(self) -> None:
        """Write benchmark data as JSON."""
        self.proof_json.write_text(json.dumps(self.data, indent=2) + "\n")

    def _write_markdown(self) -> None:
        """Write benchmark report as Markdown."""
        lines = []

        # Header
        lines.append("# FirstTry Benchmark Report")
        lines.append("")
        lines.append(f"**Generated:** {self.data['timestamp']}")
        lines.append("")

        # System snapshot
        host = self.data.get("host", {})
        python = self.data.get("python", {})
        lines.append("## System Snapshot")
        lines.append("")
        lines.append(f"- **OS:** {host.get('os', '?')} ({host.get('arch', '?')})")
        lines.append(f"- **Kernel:** {host.get('kernel', '?')}")
        lines.append(
            f"- **CPU:** {host.get('cpu_cores', '?')} cores, "
            f"{host.get('total_ram_gb', '?')} GB RAM"
        )
        lines.append(f"- **Disk Free:** {host.get('disk_free_gb', '?')} GB")
        lines.append(
            f"- **Python:** {python.get('version', '?')} " f"({python.get('executable', '?')})"
        )
        lines.append(f"- **FirstTry:** {self.data.get('firsttry', {}).get('version', '?')}")
        lines.append("")

        # Repository snapshot
        repo = self.data.get("repo", {})
        lines.append("## Repository Snapshot")
        lines.append("")
        lines.append(f"- **Files:** {repo.get('file_count', '?')}")
        lines.append(f"- **Size:** {repo.get('total_gb', '?')} GB")
        lines.append(f"- **Fingerprint:** {repo.get('fingerprint_hash', '?')}")
        lines.append("- **Top Extensions:**")
        for item in repo.get("top_extensions", [])[:5]:
            lines.append(f"  - {item['ext']}: {item['count']} files")
        lines.append("")

        # Benchmark results table
        lines.append("## Benchmark Results")
        lines.append("")
        lines.append("| Run    | Elapsed (s) | Exit Code | Cache (GB) | Cache Files |")
        lines.append("|--------|-------------|-----------|------------|-------------|")

        for run_type in ["cold", "warm"]:
            run_data = self.data.get("runs", {}).get(run_type, {})
            if run_data.get("skipped"):
                lines.append(f"| {run_type} | SKIPPED | - | - | - |")
            else:
                elapsed = run_data.get("elapsed_s", "?")
                exit_code = run_data.get("exit_code", "?")
                cache_gb = run_data.get("cache_gb", "?")
                cache_files = run_data.get("cache_files", "?")
                lines.append(
                    f"| {run_type} | {elapsed} | {exit_code} | {cache_gb} | {cache_files} |"
                )

        lines.append("")

        # Regression check
        regression = self.data.get("regression", {})
        if regression.get("detected"):
            lines.append("## ❌ Regression Detected")
            lines.append("")
            lines.append(
                f"Warm run regressed by **{regression.get('pct_change', '?')}%** "
                f"(threshold: {regression.get('threshold_pct', '?')}%)"
            )
            lines.append("")
            lines.append(f"- Prior warm: {regression.get('prior_warm_s', '?')}s")
            lines.append(f"- Current warm: {regression.get('current_warm_s', '?')}s")
            lines.append("")
        elif regression.get("prior_warm_s"):
            lines.append("## ✅ No Regression")
            lines.append("")
            lines.append(
                f"Warm run improved or stable vs baseline "
                f"(change: {regression.get('pct_change', '?')}%)"
            )
            lines.append("")

        # Observations
        lines.append("## Observations")
        lines.append("")

        cold_ok = self.data.get("runs", {}).get("cold", {}).get("ok")
        warm_ok = self.data.get("runs", {}).get("warm", {}).get("ok")
        cold_elapsed = self.data.get("runs", {}).get("cold", {}).get("elapsed_s")
        warm_elapsed = self.data.get("runs", {}).get("warm", {}).get("elapsed_s")

        if cold_ok and warm_ok:
            if warm_elapsed and cold_elapsed and warm_elapsed < cold_elapsed:
                lines.append("✅ Warm run is faster than cold (cache effective)")
            elif warm_elapsed and cold_elapsed:
                pct = (warm_elapsed - cold_elapsed) / cold_elapsed * 100
                lines.append(
                    f"⚠️ Warm run slower than cold by {pct:.1f}% "
                    "(possible cache thrash or lock contention)"
                )
        else:
            if not cold_ok:
                lines.append("❌ Cold run failed")
            if not warm_ok:
                lines.append("❌ Warm run failed")

        cache_gb = self.data.get("runs", {}).get("warm", {}).get("cache_gb", 0)
        if cache_gb and cache_gb > 5:
            lines.append(f"⚠️ Large cache: {cache_gb} GB (consider `rm -rf .firsttry/cache`)")

        file_count = self.data.get("repo", {}).get("file_count", 0)
        if file_count > 200000:
            lines.append(f"ℹ️ Large repo: {file_count} files (consider `--changed-only` mode)")

        lines.append("")

        # Recommended environment
        lines.append("## Recommended Environment")
        lines.append("")
        lines.append("```bash")
        lines.append("export FT_MAX_PROCS=" + str(self.max_procs))
        lines.append("export FT_TIMEOUT_S=" + str(self.timeout_s))
        lines.append("export FT_SEND_TELEMETRY=" + ("0" if self.no_telemetry else "1"))
        lines.append("export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1")
        lines.append("```")
        lines.append("")

        # Artifact paths
        lines.append("## Artifacts")
        lines.append("")
        lines.append(f"- JSON report: `{self.proof_json.relative_to(self.repo_root)}`")
        lines.append("- Cold log: `bench_artifacts/cold.log`")
        lines.append("- Warm log: `bench_artifacts/warm.log`")
        lines.append("")

        # Toolchain versions
        if self.data.get("tooling"):
            lines.append("## Toolchain Versions")
            lines.append("")
            for tool, version in self.data["tooling"].items():
                if version:
                    lines.append(f"- **{tool}:** {version}")
            lines.append("")

        # Git info
        if self.data.get("git"):
            git = self.data["git"]
            lines.append("## Git Info")
            lines.append("")
            if git.get("commit"):
                lines.append(f"- **Commit:** {git.get('commit')}")
            if git.get("branch"):
                lines.append(f"- **Branch:** {git.get('branch')}")
            if git.get("tag"):
                lines.append(f"- **Tag:** {git.get('tag')}")
            lines.append(f"- **Dirty:** {'Yes' if git.get('dirty') else 'No'}")
            lines.append("")

        self.proof_md.write_text("\n".join(lines))

    def _run_cmd(self, cmd: List[str], timeout: int = 30) -> str:
        """Run a command and return stdout (simple)."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return ""

    def _run_cmd_with_timing(
        self,
        cmd: List[str],
        env: Dict[str, str],
        timeout: int = 300,
        log_file: Optional[Path] = None,
    ) -> Tuple[Dict[str, Any], float]:
        """Run command with timing and optional log capture."""
        start = time.time()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )
            elapsed = time.time() - start

            # Write log if requested
            if log_file:
                log_content = f"=== COMMAND ===\n{' '.join(cmd)}\n\n=== STDOUT ===\n{result.stdout}\n\n=== STDERR ===\n{result.stderr}\n"
                log_file.write_text(log_content)

            return (
                {
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                },
                elapsed,
            )
        except subprocess.TimeoutExpired:
            elapsed = time.time() - start
            if log_file:
                log_file.write_text(
                    f"=== COMMAND ===\n{' '.join(cmd)}\n\n=== ERROR ===\nTimeout after {timeout}s\n"
                )
            return {"returncode": 124, "stdout": "", "stderr": "Timeout"}, elapsed
        except Exception as e:
            elapsed = time.time() - start
            if log_file:
                log_file.write_text(f"=== ERROR ===\n{str(e)}\n")
            return {"returncode": 1, "stdout": "", "stderr": str(e)}, elapsed

    @staticmethod
    def _get_tool_version(cmd: List[str]) -> Optional[str]:
        """Get tool version, return None if tool not found."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return None

    @staticmethod
    def _get_total_ram() -> float:
        """Get total system RAM in GB."""
        try:
            # Try reading from /proc/meminfo on Linux
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        kb = int(line.split()[1])
                        return round(kb / (1024**2), 1)
        except (FileNotFoundError, ValueError):
            pass

        # Fallback: rough estimate based on environment hints
        # (This won't be accurate but better than nothing)
        try:
            import resource

            bytes_total = resource.getrlimit(resource.RLIMIT_AS)[1]
            if bytes_total != resource.RLIM_INFINITY:
                return round(bytes_total / (1024**3), 1)
        except ImportError:
            pass

        return 0.0

    @staticmethod
    def _get_disk_free() -> float:
        """Get free disk space for current repo in GB."""
        try:
            stat = shutil.disk_usage(".")
            return round(stat.free / (1024**3), 1)
        except (OSError, PermissionError):
            return 0.0

    def _get_git_info(self) -> Dict[str, Any]:
        """Get git information if in a repo."""
        git_info: Dict[str, Any] = {}

        # Commit
        commit = self._run_cmd(["git", "rev-parse", "HEAD"], timeout=5)
        if commit:
            git_info["commit"] = commit.strip()

        # Branch
        branch = self._run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"], timeout=5)
        if branch:
            git_info["branch"] = branch.strip()

        # Tag
        tag = self._run_cmd(
            ["git", "describe", "--tags", "--exact-match"],
            timeout=5,
        )
        if tag:
            git_info["tag"] = tag.strip()

        # Dirty state
        status = self._run_cmd(["git", "status", "--porcelain"], timeout=5)
        git_info["dirty"] = bool(status.strip())

        return git_info


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="FirstTry Benchmark Harness - Cold/Warm Performance Runner"
    )
    parser.add_argument(
        "--tier",
        choices=["lite", "pro"],
        default="lite",
        help="FirstTry tier to run",
    )
    parser.add_argument(
        "--mode",
        choices=["fast", "full"],
        default="fast",
        help="FirstTry mode",
    )
    parser.add_argument(
        "--max-procs",
        type=int,
        default=None,
        help="Max parallel processes (auto-detect if not specified)",
    )
    parser.add_argument(
        "--timeout-s",
        type=int,
        default=300,
        help="Timeout per run in seconds",
    )
    parser.add_argument(
        "--no-telemetry",
        action="store_true",
        default=True,
        help="Disable FirstTry telemetry for benchmarking",
    )
    parser.add_argument(
        "--regress-pct",
        type=float,
        default=25.0,
        help="Regression threshold percentage",
    )
    parser.add_argument(
        "--skip-cold",
        action="store_true",
        help="Skip cold run",
    )
    parser.add_argument(
        "--skip-warm",
        action="store_true",
        help="Skip warm run",
    )

    args = parser.parse_args()

    runner = BenchRunner(
        tier=args.tier,
        mode=args.mode,
        max_procs=args.max_procs,
        timeout_s=args.timeout_s,
        no_telemetry=args.no_telemetry,
        regress_pct=args.regress_pct,
        skip_cold=args.skip_cold,
        skip_warm=args.skip_warm,
    )

    return runner.run()


if __name__ == "__main__":
    sys.exit(main())
