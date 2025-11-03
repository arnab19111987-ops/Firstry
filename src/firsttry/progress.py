import sys

def step(msg: str) -> None:
    """Print a major step message"""
    sys.stdout.write(f"🔹 {msg}\n")
    sys.stdout.flush()

def tick(msg: str) -> None:
    """Print a sub-step message"""
    sys.stdout.write(f"  • {msg}\n")
    sys.stdout.flush()

def done(msg: str) -> None:
    """Print a completion message"""
    sys.stdout.write(f"  ✅ {msg}\n")
    sys.stdout.flush()

def fail(msg: str) -> None:
    """Print a failure message"""
    sys.stdout.write(f"  ❌ {msg}\n")
    sys.stdout.flush()

def cached(msg: str) -> None:
    """Print a cached result message"""
    sys.stdout.write(f"  ⚡ {msg} (cached)\n")
    sys.stdout.flush()

def bucket_header(bucket: str, count: int) -> None:
    """Print bucket execution header"""
    icons = {
        "fast": "⚡",
        "mutating": "🛠️",  
        "slow": "🐌"
    }
    icon = icons.get(bucket, "🔧")
    sys.stdout.write(f"\n{icon} {bucket.upper()} ({count} checks)\n")
    sys.stdout.flush()

def summary_header() -> None:
    """Print summary section header"""
    sys.stdout.write("\n── Summary ──\n")
    sys.stdout.flush()