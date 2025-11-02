"""
Config caching and timeout handling for remote configuration.
"""
import json
import os
import time
from pathlib import Path
from typing import Dict, List, Any, Optional


def _get_cache_dir() -> Path:
    """Get the .firsttry/cache directory."""
    cache_dir = Path.cwd() / ".firsttry" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _get_config_cache_path() -> Path:
    """Get the path to the config cache file."""
    return _get_cache_dir() / "config.json"


def _save_config_to_cache(config_plan: List[Dict[str, Any]], repo_key: str) -> None:
    """Save a successful config plan to cache with repo versioning."""
    cache_path = _get_config_cache_path()
    
    cache_data = {}
    if cache_path.exists():
        try:
            with open(cache_path, "r") as f:
                cache_data = json.load(f)
        except (json.JSONDecodeError, OSError):
            cache_data = {}
    
    cache_data[repo_key] = {
        "plan": config_plan,
        "timestamp": time.time(),
        "version": "1.0"
    }
    
    try:
        with open(cache_path, "w") as f:
            json.dump(cache_data, f, indent=2)
    except OSError:
        # If we can't write cache, that's OK - we'll just work without it
        pass


def _load_config_from_cache(repo_key: str) -> Optional[List[Dict[str, Any]]]:
    """Load cached config plan for this repo if it exists and is recent."""
    cache_path = _get_config_cache_path()
    
    if not cache_path.exists():
        return None
    
    try:
        with open(cache_path, "r") as f:
            cache_data = json.load(f)
        
        repo_data = cache_data.get(repo_key)
        if not repo_data:
            return None
        
        # Check if cache is too old (older than 24 hours)
        age = time.time() - repo_data.get("timestamp", 0)
        if age > 86400:  # 24 hours
            return None
        
        return repo_data.get("plan")
        
    except (json.JSONDecodeError, OSError, KeyError):
        return None


def _get_repo_key() -> str:
    """Generate a unique key for this repository."""
    try:
        # Use git remote origin URL if available
        import subprocess
        remote = subprocess.check_output(
            ["git", "config", "--get", "remote.origin.url"], 
            cwd=".", 
            stderr=subprocess.DEVNULL,
            timeout=2
        )
        return remote.decode().strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        # Fall back to current directory path
        return str(Path.cwd().absolute())


class ConfigTimeoutError(Exception):
    """Raised when config operation times out."""
    pass


def plan_from_config_with_timeout(
    config: Dict[str, Any], 
    timeout_seconds: float = 2.5
) -> Optional[List[Dict[str, Any]]]:
    """
    Load config plan with timeout and caching.
    
    Args:
        config: Configuration dictionary
        timeout_seconds: Timeout for config operations (default 2.5s)
    
    Returns:
        Config plan or None if not available/timeout
    """
    from .config_loader import plan_from_config
    import concurrent.futures
    import signal
    
    # Generate repo key for cache versioning
    repo_key = _get_repo_key()
    
    try:
        # Use ThreadPoolExecutor with timeout for safer execution
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(plan_from_config, config)
            try:
                plan = future.result(timeout=timeout_seconds)
                
                # If successful, cache the result
                if plan:
                    _save_config_to_cache(plan, repo_key)
                
                return plan
                
            except concurrent.futures.TimeoutError:
                print("⚠️ Remote config unavailable, using local plan")
                
                # Try to load from cache as fallback
                cached_plan = _load_config_from_cache(repo_key)
                if cached_plan:
                    print("   Using cached config from previous run")
                    return cached_plan
                
                # No cache available
                return None
            
    except Exception as e:
        # Any other error - try cache
        print(f"⚠️ Config error ({e}), using local plan")
        cached_plan = _load_config_from_cache(repo_key)
        if cached_plan:
            print("   Using cached config from previous run")
            return cached_plan
        
        return None