#!/usr/bin/env python3
"""
FirstTry Benchmark Readiness Auditor

Repo-agnostic readiness check for running cold/warm benchmark tests.
Produces a Markdown report with pass/fail checks and actionable fixes.

Exit codes:
  0 = READY (all checks pass)
  2 = PARTIAL (warnings, but can proceed)
  3 = BLOCKED (critical issues)
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple


class AuditResult:
    """Encapsulates a single audit check result."""

    def __init__(self, name: str, status: str):
        self.name = name
        self.status = status  # PASS, PARTIAL, BLOCK
        self.emoji = {"PASS": "✅", "PARTIAL": "⚠️", "BLOCK": "❌"}[status]
        self.details: List[str] = []
        self.fixes: List[str] = []

    def add_detail(self, text: str):
        self.details.append(text)

    def add_fix(self, text: str):
        self.fixes.append(text)

    def to_markdown(self) -> str:
        lines = [f"## {self.emoji} {self.name}"]
        if self.details:
            lines.append("")
            for detail in self.details:
                lines.append(detail)
        if self.fixes:
            lines.append("")
            lines.append("**How to fix:**")
            for fix in self.fixes:
                lines.append(f"- {fix}")
        lines.append("")
        return "\n".join(lines)


def run(cmd: List[str], timeout: int = 30, capture: bool = True) -> Tuple[int, str, str, float]:
    """
    Run a command safely with timeout.
    Returns (returncode, stdout, stderr, elapsed_seconds)
    """
    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            timeout=timeout,
        )
        elapsed = time.time() - start
        return result.returncode, result.stdout, result.stderr, elapsed
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        return 124, "", f"Command timed out after {timeout}s", elapsed
    except FileNotFoundError:
        elapsed = time.time() - start
        return 127, "", f"Command not found: {cmd[0]}", elapsed
    except Exception as e:
        elapsed = time.time() - start
        return 1, "", str(e), elapsed


def truncate_log(text: str, max_lines: int = 20) -> str:
    """Truncate log output for readability."""
    lines = text.split("\n")
    if len(lines) > max_lines:
        return "\n".join(lines[:max_lines]) + f"\n... ({len(lines) - max_lines} more lines)"
    return text


def get_system_info() -> Dict[str, Any]:
    """Gather system information."""
    try:
        mem_gb = 0
        if os.path.exists("/proc/meminfo"):
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        mem_gb = int(line.split()[1]) / (1024 * 1024)
                        break
        else:
            # Fallback for non-Linux
            try:
                import psutil

                mem_gb = psutil.virtual_memory().total / (1024**3)
            except Exception:
                mem_gb = 0

        return {
            "os": platform.system(),
            "arch": platform.machine(),
            "python_version": platform.python_version(),
            "cpu_count": os.cpu_count() or 1,
            "memory_gb": round(mem_gb, 1),
        }
    except Exception as e:
        return {"error": str(e)}


def get_disk_free() -> float:
    """Get free disk space in GB for current directory."""
    try:
        stat = shutil.disk_usage(".")
        return stat.free / (1024**3)
    except Exception:
        return 0


def get_repo_size() -> float:
    """Estimate repo size in GB."""
    try:
        result = subprocess.run(
            ["du", "-sb", "."],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return int(result.stdout.split()[0]) / (1024**3)
    except Exception:
        pass
    return 0


def scan_repo_tree() -> Dict[str, Any]:
    """Fast scan of repo tree with excludes."""
    excludes = {
        ".git",
        ".venv",
        ".venv-build",
        ".venv-dev",
        "node_modules",
        "dist",
        "build",
        ".next",
        "coverage",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".vscode",
        ".idea",
        "venv",
        "env",
    }

    binary_exts = {
        ".parquet",
        ".zip",
        ".tar",
        ".gz",
        ".jar",
        ".bin",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".pdf",
        ".mp4",
        ".mov",
        ".iso",
    }

    file_count = 0
    total_bytes = 0
    extensions: Dict[str, int] = {}
    largest_files: List[Tuple[str, int]] = []
    dir_sizes: Dict[str, int] = {}

    start_time = time.time()
    max_files = 500000
    timeout_seconds = 30

    try:
        for root, dirs, files in os.walk(".", topdown=True):
            # Remove excluded dirs
            dirs[:] = [d for d in dirs if d not in excludes]

            # Check timeout
            if time.time() - start_time > timeout_seconds:
                return {
                    "status": "PARTIAL",
                    "file_count": file_count,
                    "total_bytes": total_bytes,
                    "truncated": True,
                    "message": f"Scan timeout after {timeout_seconds}s",
                }

            if file_count > max_files:
                return {
                    "status": "PARTIAL",
                    "file_count": file_count,
                    "total_bytes": total_bytes,
                    "truncated": True,
                    "message": f"Truncated after {max_files} files",
                }

            dir_key = root.replace("./", "")
            dir_bytes = 0

            for f in files:
                file_count += 1
                fpath = os.path.join(root, f)

                try:
                    fsize = os.path.getsize(fpath)
                    total_bytes += fsize
                    dir_bytes += fsize

                    # Track extension
                    ext = Path(f).suffix.lower()
                    if ext:
                        extensions[ext] = extensions.get(ext, 0) + 1

                    # Track largest files
                    if ext not in binary_exts:
                        largest_files.append((fpath, fsize))

                except (OSError, IOError):
                    pass

            if dir_bytes > 0:
                dir_sizes[dir_key] = dir_bytes

    except Exception as e:
        return {
            "status": "ERROR",
            "error": str(e),
            "file_count": file_count,
            "total_bytes": total_bytes,
        }

    # Sort largest files
    largest_files.sort(key=lambda x: x[1], reverse=True)
    largest_files = largest_files[:10]

    # Sort dirs by size
    sorted_dirs = sorted(dir_sizes.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "status": "OK",
        "file_count": file_count,
        "total_bytes": total_bytes,
        "extensions": dict(sorted(extensions.items(), key=lambda x: x[1], reverse=True)[:10]),
        "largest_files": [(p, s) for p, s in largest_files],
        "largest_dirs": [(d, s) for d, s in sorted_dirs],
        "truncated": False,
    }


def detect_languages(tree_info: Dict[str, Any]) -> List[str]:
    """Detect languages based on file extensions."""
    languages = []
    extensions = tree_info.get("extensions", {})

    if any(ext in extensions for ext in [".py"]):
        languages.append("Python")
    if any(ext in extensions for ext in [".js", ".ts", ".jsx", ".tsx"]):
        languages.append("JavaScript/TypeScript")
    if any(ext in extensions for ext in [".go"]):
        languages.append("Go")
    if any(ext in extensions for ext in [".rs"]):
        languages.append("Rust")
    if any(ext in extensions for ext in [".java", ".kotlin"]):
        languages.append("Java/Kotlin")
    if any(ext in extensions for ext in [".c", ".cpp", ".h", ".hpp"]):
        languages.append("C/C++")
    if any(ext in extensions for ext in [".Dockerfile", "Dockerfile"]):
        languages.append("Docker")
    if any(ext in extensions for ext in [".tf"]):
        languages.append("Terraform")
    if any(ext in extensions for ext in [".yml", ".yaml"]):
        languages.append("YAML")

    return languages or ["Mixed/Unknown"]


def audit_cli_presence() -> AuditResult:
    """Check 1: FirstTry CLI presence & version."""
    result = AuditResult("FirstTry CLI Presence & Version", "PASS")

    code, out, err, _ = run(
        [sys.executable, "-m", "firsttry", "--version"],
        timeout=5,
    )

    if code == 0:
        version = out.strip()
        result.add_detail(f"✓ FirstTry CLI found: {version}")
    else:
        result.status = "BLOCK"
        result.add_detail(f"✗ FirstTry CLI not found or failed: {err}")
        result.add_fix("Install FirstTry: `pip install firsttry`")
        result.add_fix("Or for dev: `pip install -e .` (in repo root)")
        return result

    # Check help
    code, out, err, _ = run(
        [sys.executable, "-m", "firsttry", "run", "--help"],
        timeout=5,
    )
    if code == 0:
        result.add_detail("✓ CLI help accessible")
    else:
        result.status = "BLOCK"
        result.add_detail(f"✗ CLI help failed: {err}")
        result.add_fix("Reinstall or upgrade FirstTry")

    return result


def audit_cli_args(help_text: str) -> AuditResult:
    """Check 2: CLI arg parity & critical flags."""
    result = AuditResult("CLI Argument Parity", "PASS")

    required_flags = [
        "--tier",
        "--profile",
        "--source",
        "--changed-only",
        "--no-cache",
        "--cache-only",
        "--debug-phases",
        "--report-json",
        "--show-report",
        "--report-schema",
        "--dry-run",
    ]

    missing = []
    for flag in required_flags:
        if flag not in help_text:
            missing.append(flag)

    if missing:
        result.status = "BLOCK"
        result.add_detail(f"✗ Missing CLI flags: {', '.join(missing)}")
        result.add_fix("Upgrade FirstTry: `pip install --upgrade firsttry`")
        result.add_fix("Or sync CLI parser if developing locally")
    else:
        result.add_detail(f"✓ All {len(required_flags)} critical flags present")

    return result


def audit_environment() -> AuditResult:
    """Check 3: Environment & toolchain sanity."""
    result = AuditResult("Environment & Toolchain", "PASS")

    info = get_system_info()
    result.add_detail(f"OS: {info.get('os')} ({info.get('arch')})")
    result.add_detail(f"Python: {info.get('python_version')}")
    result.add_detail(f"CPU cores: {info.get('cpu_count')}")

    py_ver = sys.version_info
    if py_ver.major < 3 or (py_ver.major == 3 and py_ver.minor < 10):
        result.status = "BLOCK"
        result.add_detail(f"✗ Python {py_ver.major}.{py_ver.minor} < 3.10")
        result.add_fix("Upgrade to Python 3.10+")
    else:
        result.add_detail(f"✓ Python {py_ver.major}.{py_ver.minor} is acceptable")

    # Memory check
    mem_gb = info.get("memory_gb", 0)
    if mem_gb > 0:
        result.add_detail(f"Memory: {mem_gb:.1f} GB")
        if mem_gb < 4:
            result.status = "PARTIAL" if result.status == "PASS" else result.status
            result.add_detail("⚠️ Warning: < 4 GB RAM; large repos may be slow")
            result.add_fix("Consider adding more RAM or using --changed-only")

    # Disk space check
    repo_size = get_repo_size()
    disk_free = get_disk_free()
    result.add_detail(f"Disk free: {disk_free:.1f} GB (repo ~{repo_size:.1f} GB)")

    min_free = max(repo_size * 2, 10)
    if disk_free < min_free:
        result.status = "PARTIAL" if result.status == "PASS" else result.status
        result.add_detail(f"⚠️ Warning: Free space ({disk_free:.1f} GB) < {min_free:.1f} GB needed")
        result.add_fix("Free up disk space or use smaller subsets of the repo")

    # Node check (optional)
    code, node_ver, _, _ = run(["node", "--version"], timeout=2)
    if code == 0:
        result.add_detail(f"Node: {node_ver.strip()}")
    else:
        result.add_detail("Node: not found (optional)")

    # npm check (optional)
    code, npm_ver, _, _ = run(["npm", "--version"], timeout=2)
    if code == 0:
        result.add_detail(f"npm: {npm_ver.strip()}")

    return result


def audit_license_tier() -> AuditResult:
    """Check 4: License & tier resolution."""
    result = AuditResult("License & Tier Resolution", "PASS")

    has_key = "FT_LICENSE_KEY" in os.environ
    result.add_detail(f"License key env: {'set' if has_key else 'not set'}")

    # Try license status command
    code, out, err, _ = run(
        [sys.executable, "-m", "firsttry", "license", "status"],
        timeout=5,
    )

    if code == 0:
        result.add_detail(f"License status: {out.strip()[:100]}")
    else:
        # Fallback: try dry-run to infer tier
        code, out, err, _ = run(
            [sys.executable, "-m", "firsttry", "run", "q", "--tier", "lite", "--dry-run"],
            timeout=10,
        )
        if code == 0:
            result.add_detail("Tier inference: lite (dry-run succeeded)")
        else:
            result.status = "PARTIAL"
            result.add_detail("⚠️ Could not determine tier; license may be needed for pro features")
            result.add_fix("Set FT_LICENSE_KEY if you have a license")
            result.add_fix("Or use --tier lite for free tier testing")

    return result


def audit_cache_health() -> AuditResult:
    """Check 5: Cache health."""
    result = AuditResult("Cache Health", "PASS")

    cache_dir = Path(os.environ.get("FT_CACHE_DIR", ".firsttry/cache"))
    result.add_detail(f"Cache dir: {cache_dir}")

    if cache_dir.exists():
        result.add_detail("✓ Cache directory exists")

        # Check write perms
        try:
            test_file = cache_dir / ".write_test"
            test_file.write_text("test")
            test_file.unlink()
            result.add_detail("✓ Cache is writable")
        except Exception as e:
            result.status = "BLOCK"
            result.add_detail(f"✗ Cache not writable: {e}")
            result.add_fix(f"Fix permissions: chmod -R u+w {cache_dir}")

        # Check age
        try:
            mtime = cache_dir.stat().st_mtime
            age_days = (time.time() - mtime) / 86400
            result.add_detail(f"Cache age: {age_days:.1f} days")
            if age_days > 7:
                result.status = "PARTIAL" if result.status == "PASS" else result.status
                result.add_detail("⚠️ Cache is stale (>7 days)")
                result.add_fix(f"Purge old cache: rm -rf {cache_dir}")
        except Exception:
            pass
    else:
        result.add_detail("Cache directory does not exist (will be created on first run)")

    return result


def audit_repo_scale() -> AuditResult:
    """Check 6: Repo scale scan (fast & safe)."""
    result = AuditResult("Repository Scale", "PASS")

    tree_info = scan_repo_tree()

    if tree_info.get("status") == "ERROR":
        result.status = "BLOCK"
        result.add_detail(f"✗ Scan error: {tree_info.get('error')}")
        result.add_fix("Check directory permissions and available disk space")
        return result

    file_count = tree_info.get("file_count", 0)
    total_bytes = tree_info.get("total_bytes", 0)
    total_gb = total_bytes / (1024**3)

    result.add_detail(f"File count: {file_count:,}")
    result.add_detail(f"Total size: {total_gb:.2f} GB")

    if tree_info.get("truncated"):
        result.add_detail(f"⚠️ {tree_info.get('message')}")
        result.status = "PARTIAL"

    # Warn if very large
    if file_count > 200000 or total_gb > 5:
        result.status = "PARTIAL"
        result.add_detail("⚠️ Large repository detected")
        result.add_fix("Consider using --changed-only for initial benchmarks")
        result.add_fix("Or scope to specific directories with --source")

    # Show extensions
    exts = tree_info.get("extensions", {})
    if exts:
        top_exts = list(exts.items())[:5]
        result.add_detail(f"Top extensions: {', '.join(f'{k}({v})' for k, v in top_exts)}")

    # Show largest dirs
    dirs = tree_info.get("largest_dirs", [])
    if dirs:
        result.add_detail("Largest directories (top 3):")
        for d, s in dirs[:3]:
            result.add_detail(f"  {d}: {s / (1024**2):.1f} MB")

    return result


def audit_language_gates(tree_info: Dict[str, Any]) -> AuditResult:
    """Check 7: Language detection vs Gates."""
    result = AuditResult("Language Detection & Gates", "PASS")

    languages = detect_languages(tree_info)
    result.add_detail(f"Detected languages: {', '.join(languages)}")

    # Map languages to gate requirements
    gate_map = {
        "Python": ["ruff", "mypy", "pytest"],
        "JavaScript/TypeScript": ["eslint"],
        "Go": [],
        "Rust": ["cargo"],
        "Docker": ["hadolint (optional)"],
        "Terraform": ["terraform validate"],
    }

    detected_gates = []
    for lang in languages:
        gates = gate_map.get(lang, [])
        detected_gates.extend(gates)

    if detected_gates:
        result.add_detail(f"Expected gates: {', '.join(set(detected_gates))}")
    else:
        result.add_detail("⚠️ No standard gates detected; may use custom checks")

    result.add_detail("\nFor lite tier: ruff, mypy, pytest (Python)")
    result.add_detail("For pro tier: above + bandit, coverage checks")

    return result


def audit_dry_run() -> AuditResult:
    """Check 8: CI parity probe (dry run)."""
    result = AuditResult("CI Parity Probe (Dry Run)", "PASS")

    cmd = [
        sys.executable,
        "-m",
        "firsttry",
        "run",
        "q",
        "--tier",
        "lite",
        "--dry-run",
        "--debug-phases",
    ]

    result.add_detail(f"Running: {' '.join(cmd)}")
    code, out, err, elapsed = run(cmd, timeout=15)

    result.add_detail(f"Exit code: {code}, elapsed: {elapsed:.2f}s")

    if code == 0:
        result.add_detail("✓ Dry run succeeded; CLI is functional")
        # Show first few lines of output
        if out:
            lines = out.split("\n")[:5]
            result.add_detail("Output excerpt:")
            for line in lines:
                if line.strip():
                    result.add_detail(f"  {line}")
    else:
        result.status = "BLOCK"
        result.add_detail("✗ Dry run failed")
        if err:
            result.add_detail(f"Error: {truncate_log(err, 10)}")
        result.add_fix("Check FirstTry installation or config")
        result.add_fix("Run with --debug to see detailed logs")

    return result


def audit_safety_settings() -> AuditResult:
    """Check 9: Safety timeouts & parallelism."""
    result = AuditResult("Safety & Parallelism Settings", "PASS")

    cpu_count = os.cpu_count() or 1
    recommended_procs = min(cpu_count, 8)

    result.add_detail(f"CPU cores: {cpu_count}")
    result.add_detail(f"Recommended FT_MAX_PROCS: {recommended_procs}")
    result.add_detail("Recommended FT_TIMEOUT_S: 300")

    has_timeout_override = "FT_TIMEOUT_S" in os.environ
    has_procs_override = "FT_MAX_PROCS" in os.environ

    result.add_detail(f"FT_TIMEOUT_S set: {has_timeout_override}")
    result.add_detail(f"FT_MAX_PROCS set: {has_procs_override}")

    if not has_procs_override:
        result.status = "PARTIAL"
        result.add_detail("⚠️ FT_MAX_PROCS not set; using default")
        result.add_fix(f"Export: export FT_MAX_PROCS={recommended_procs}")

    return result


def audit_telemetry() -> AuditResult:
    """Check 10: Telemetry & reproducibility."""
    result = AuditResult("Telemetry & Reproducibility", "PASS")

    telemetry_enabled = os.environ.get("FT_SEND_TELEMETRY", "").lower() not in (
        "0",
        "false",
        "no",
    )

    result.add_detail(f"Telemetry enabled: {telemetry_enabled}")

    if telemetry_enabled:
        result.status = "PARTIAL"
        result.add_detail("⚠️ Telemetry is enabled; may affect benchmark timing")
        result.add_fix("Disable for clean benchmarks: export FT_SEND_TELEMETRY=0")

    result.add_detail("Tool version pinning recommended for reproducibility")
    result.add_fix("Commit requirements.txt or poetry.lock to version control")

    return result


def main():
    parser = argparse.ArgumentParser(description="FirstTry Benchmark Readiness Auditor")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON instead of Markdown",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Include verbose details",
    )
    args = parser.parse_args()

    # Gather info
    system_info = get_system_info()
    repo_info = scan_repo_tree()

    # Get CLI help text early
    code, help_text, _, _ = run(
        [sys.executable, "-m", "firsttry", "run", "--help"],
        timeout=5,
    )
    if code != 0:
        help_text = ""

    # Run all audits
    audits = [
        audit_cli_presence(),
        audit_cli_args(help_text),
        audit_environment(),
        audit_license_tier(),
        audit_cache_health(),
        audit_repo_scale(),
        audit_language_gates(repo_info),
        audit_dry_run(),
        audit_safety_settings(),
        audit_telemetry(),
    ]

    # Determine overall status
    statuses = [a.status for a in audits]
    if "BLOCK" in statuses:
        overall_status = "HOLD"
        exit_code = 3
    elif "PARTIAL" in statuses:
        overall_status = "PARTIAL"
        exit_code = 2
    else:
        overall_status = "GO"
        exit_code = 0

    if args.json:
        # JSON output
        result_dict = {
            "status": overall_status,
            "exit_code": exit_code,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "system": system_info,
            "audits": [
                {
                    "name": a.name,
                    "status": a.status,
                    "details": a.details,
                    "fixes": a.fixes,
                }
                for a in audits
            ],
        }
        print(json.dumps(result_dict, indent=2))
    else:
        # Markdown output
        lines = [
            "# FirstTry Benchmark Readiness Audit",
            "",
            f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Status:** {overall_status}",
            "",
            "## System Information",
            f"- **OS:** {system_info.get('os')} ({system_info.get('arch')})",
            f"- **Python:** {system_info.get('python_version')}",
            f"- **CPU Cores:** {system_info.get('cpu_count')}",
            f"- **Memory:** {system_info.get('memory_gb', 0):.1f} GB",
            f"- **Disk Free:** {get_disk_free():.1f} GB",
            "",
            "## Audit Results",
            "",
        ]

        # Summary table
        lines.append("| Check | Status |")
        lines.append("|-------|--------|")
        for audit in audits:
            lines.append(f"| {audit.name} | {audit.emoji} |")

        lines.append("")
        lines.append("## Detailed Results")
        lines.append("")

        # Detailed sections
        for audit in audits:
            lines.append(audit.to_markdown())

        # Build benchmark commands
        cpu_count = os.cpu_count() or 1
        rec_procs = min(cpu_count, 8)

        lines.append("## Next Steps")
        lines.append("")

        if overall_status == "HOLD":
            lines.append("❌ **BLOCKED** - Fix critical issues above before proceeding.")
        elif overall_status == "PARTIAL":
            lines.append(
                "⚠️ **PARTIAL** - Address warnings above for best results, but you can proceed."
            )
        else:
            lines.append("✅ **READY** - Proceed with benchmarking!")

        lines.append("")
        lines.append("### Recommended Environment")
        lines.append("")
        lines.append("```bash")
        lines.append(f"export FT_MAX_PROCS={rec_procs}")
        lines.append("export FT_TIMEOUT_S=300")
        lines.append("export FT_SEND_TELEMETRY=0")
        lines.append("export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1")
        lines.append("```")
        lines.append("")

        lines.append("### Cold Run (Clear Cache)")
        lines.append("")
        lines.append("```bash")
        lines.append("rm -rf .firsttry/cache")
        lines.append("FT_MAX_PROCS=${FT_MAX_PROCS:-" + str(rec_procs) + "} \\\n")
        lines.append("  FT_TIMEOUT_S=300 FT_SEND_TELEMETRY=0 \\\n")
        lines.append("  python -m firsttry run fast --tier lite --no-cache --show-report")
        lines.append("```")
        lines.append("")

        lines.append("### Warm Run (With Cache)")
        lines.append("")
        lines.append("```bash")
        lines.append("FT_MAX_PROCS=${FT_MAX_PROCS:-" + str(rec_procs) + "} \\\n")
        lines.append("  FT_TIMEOUT_S=300 FT_SEND_TELEMETRY=0 \\\n")
        lines.append("  python -m firsttry run fast --tier lite --show-report")
        lines.append("```")
        lines.append("")

        # Check for license
        if "FT_LICENSE_KEY" in os.environ:
            lines.append("### Pro Tier (With License)")
            lines.append("")
            lines.append("```bash")
            lines.append("FT_LICENSE_KEY=*** \\\n")
            lines.append("  FT_MAX_PROCS=${FT_MAX_PROCS:-" + str(rec_procs) + "} \\\n")
            lines.append("  FT_TIMEOUT_S=300 \\\n")
            lines.append("  python -m firsttry run pro --show-report")
            lines.append("```")
            lines.append("")

        print("\n".join(lines))

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
