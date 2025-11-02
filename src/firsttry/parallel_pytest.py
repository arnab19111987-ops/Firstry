from __future__ import annotations
import asyncio
import json
import math
import os
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Set, Any, Optional, Tuple

from . import cache as ft_cache


def discover_all_tests(repo_root: str) -> List[str]:
    """Discover all test files in the repository"""
    repo_path = Path(repo_root)
    test_files = []
    
    # Common test patterns
    test_patterns = [
        "tests/**/*test*.py",
        "test/**/*test*.py", 
        "src/**/test_*.py",
        "**/test_*.py"
    ]
    
    for pattern in test_patterns:
        matches = list(repo_path.glob(pattern))
        for match in matches:
            rel_path = str(match.relative_to(repo_path))
            if rel_path not in test_files:
                test_files.append(rel_path)
    
    return sorted(test_files)


def count_tests_in_file(repo_root: str, test_file: str) -> int:
    """Count number of tests in a specific test file"""
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "--collect-only", "-q", test_file],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            # Count test items from pytest collection output
            lines = result.stdout.split('\n')
            test_count = 0
            for line in lines:
                if '::' in line and 'test' in line.lower():
                    test_count += 1
            return test_count
        else:
            # Fallback: count test functions by parsing file
            return count_test_functions_in_file(repo_root, test_file)
            
    except Exception:
        return count_test_functions_in_file(repo_root, test_file)


def count_test_functions_in_file(repo_root: str, test_file: str) -> int:
    """Fallback: count test functions by parsing the file"""
    try:
        file_path = Path(repo_root) / test_file
        if not file_path.exists():
            return 0
            
        content = file_path.read_text(encoding='utf-8')
        lines = content.split('\n')
        
        test_count = 0
        for line in lines:
            stripped = line.strip()
            if (stripped.startswith('def test_') or 
                stripped.startswith('async def test_') or
                'def test' in stripped):
                test_count += 1
                
        return test_count
        
    except Exception:
        return 1  # Assume at least 1 test if we can't count


def analyze_test_suite(repo_root: str) -> Dict[str, Any]:
    """Analyze test suite to determine chunking strategy"""
    test_files = discover_all_tests(repo_root)
    
    if not test_files:
        return {
            "total_files": 0,
            "total_tests": 0,
            "files": [],
            "chunking_recommended": False
        }
    
    # Count tests in each file (sample first few for speed)
    file_test_counts = {}
    sample_files = test_files[:min(10, len(test_files))]  # Sample for speed
    
    total_estimated_tests = 0
    for test_file in sample_files:
        count = count_tests_in_file(repo_root, test_file)
        file_test_counts[test_file] = count
        total_estimated_tests += count
    
    # Estimate total tests based on sample
    if sample_files:
        avg_tests_per_file = total_estimated_tests / len(sample_files)
        estimated_total = int(avg_tests_per_file * len(test_files))
    else:
        estimated_total = len(test_files)  # Assume 1 test per file
    
    return {
        "total_files": len(test_files),
        "total_tests": estimated_total,
        "files": test_files,
        "sample_counts": file_test_counts,
        "chunking_recommended": estimated_total > 100  # Chunk if >100 tests
    }


def create_test_chunks(
    test_files: List[str], 
    max_workers: int = None,
    target_chunk_size: int = None
) -> List[List[str]]:
    """Split test files into balanced chunks for parallel execution"""
    
    if not test_files:
        return []
    
    # Determine optimal chunk count
    if max_workers is None:
        max_workers = min(4, os.cpu_count() or 2)
    
    if target_chunk_size is None:
        # Aim for 20-50 test files per chunk
        target_chunk_size = max(1, len(test_files) // max_workers)
        target_chunk_size = min(50, max(10, target_chunk_size))
    
    chunk_count = min(max_workers, math.ceil(len(test_files) / target_chunk_size))
    
    # Simple round-robin distribution
    chunks = [[] for _ in range(chunk_count)]
    for i, test_file in enumerate(test_files):
        chunk_idx = i % chunk_count
        chunks[chunk_idx].append(test_file)
    
    # Remove empty chunks
    return [chunk for chunk in chunks if chunk]


async def run_pytest_chunk(
    repo_root: str,
    chunk_files: List[str],
    chunk_id: int,
    extra_args: List[str] = None
) -> Dict[str, Any]:
    """Run pytest on a specific chunk of test files"""
    
    if not chunk_files:
        return {
            "chunk_id": chunk_id,
            "status": "skipped",
            "files": [],
            "output": "No test files in chunk"
        }
    
    # Build pytest command for this chunk
    cmd = ["python", "-m", "pytest", "-v", "--tb=short"]
    
    if extra_args:
        cmd.extend(extra_args)
    
    # Add test files
    cmd.extend(chunk_files)
    
    start_time = time.time()
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=repo_root,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )
        
        stdout, _ = await process.communicate()
        duration = time.time() - start_time
        
        output = stdout.decode('utf-8', 'replace')
        success = process.returncode == 0
        
        return {
            "chunk_id": chunk_id,
            "status": "ok" if success else "fail",
            "exit_code": process.returncode,
            "files": chunk_files,
            "file_count": len(chunk_files),
            "duration": duration,
            "output": output
        }
        
    except Exception as e:
        return {
            "chunk_id": chunk_id,
            "status": "error",
            "files": chunk_files,
            "duration": time.time() - start_time,
            "error": str(e),
            "output": f"Error running chunk {chunk_id}: {e}"
        }


def aggregate_chunk_results(chunk_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate results from multiple test chunks"""
    
    if not chunk_results:
        return {
            "status": "error",
            "total_chunks": 0,
            "successful_chunks": 0,
            "failed_chunks": 0,
            "total_duration": 0,
            "output": "No chunks executed"
        }
    
    successful_chunks = sum(1 for r in chunk_results if r["status"] == "ok")
    failed_chunks = sum(1 for r in chunk_results if r["status"] == "fail")
    error_chunks = sum(1 for r in chunk_results if r["status"] == "error")
    
    total_duration = max((r.get("duration", 0) for r in chunk_results), default=0)
    total_files = sum(r.get("file_count", 0) for r in chunk_results)
    
    # Aggregate output
    output_lines = []
    output_lines.append(f"=== Parallel pytest execution with {len(chunk_results)} chunks ===")
    output_lines.append(f"Total test files: {total_files}")
    output_lines.append(f"Successful chunks: {successful_chunks}")
    output_lines.append(f"Failed chunks: {failed_chunks}")
    output_lines.append(f"Error chunks: {error_chunks}")
    output_lines.append(f"Total duration: {total_duration:.2f}s (parallel)")
    output_lines.append("")
    
    # Add chunk summaries
    for result in chunk_results:
        chunk_id = result["chunk_id"]
        status = result["status"]
        duration = result.get("duration", 0)
        file_count = result.get("file_count", 0)
        
        status_icon = "✅" if status == "ok" else "❌" if status == "fail" else "⚠️"
        output_lines.append(f"{status_icon} Chunk {chunk_id}: {file_count} files, {duration:.2f}s")
    
    # Add failed chunk details
    failed_results = [r for r in chunk_results if r["status"] != "ok"]
    if failed_results:
        output_lines.append("\n=== Failed chunk details ===")
        for result in failed_results:
            output_lines.append(f"\nChunk {result['chunk_id']} ({result['status']}):")
            output_lines.append(result.get("output", "No output")[:500])  # Truncate
    
    overall_status = "ok" if failed_chunks == 0 and error_chunks == 0 else "fail"
    
    return {
        "status": overall_status,
        "total_chunks": len(chunk_results),
        "successful_chunks": successful_chunks,
        "failed_chunks": failed_chunks,
        "error_chunks": error_chunks,
        "total_files": total_files,
        "total_duration": total_duration,
        "chunk_results": chunk_results,
        "output": "\n".join(output_lines)
    }


async def run_parallel_pytest(
    repo_root: str,
    test_files: List[str] | None = None,
    max_workers: int = None,
    use_cache: bool = True,
    extra_args: List[str] = None
) -> Dict[str, Any]:
    """
    Run pytest in parallel chunks for large test suites.
    Falls back to regular pytest for small suites.
    """
    
    # Discover tests if not provided
    if test_files is None:
        analysis = analyze_test_suite(repo_root)
        test_files = analysis["files"]
        
        if not analysis["chunking_recommended"]:
            # Small test suite - run normally
            return await _run_single_pytest(repo_root, test_files, extra_args)
    
    if not test_files:
        return {
            "status": "skipped",
            "output": "No test files found",
            "chunking_used": False
        }
    
    # Check cache
    if use_cache:
        repo_path = Path(repo_root)
        all_test_paths = [repo_path / f for f in test_files]
        input_hash = ft_cache.sha256_of_paths(all_test_paths)
        
        if ft_cache.is_tool_cache_valid(repo_root, "pytest_parallel", input_hash):
            return {
                "status": "ok",
                "cached": True,
                "output": f"Parallel pytest results cached ({len(test_files)} files)",
                "chunking_used": True
            }
    
    # Create chunks
    max_workers = max_workers or min(4, os.cpu_count() or 2)
    chunks = create_test_chunks(test_files, max_workers)
    
    if len(chunks) <= 1:
        # Not worth chunking
        return await _run_single_pytest(repo_root, test_files, extra_args)
    
    print(f"🧪 Running pytest in {len(chunks)} parallel chunks ({len(test_files)} test files)")
    
    # Run chunks in parallel
    chunk_tasks = []
    for i, chunk_files in enumerate(chunks):
        task = run_pytest_chunk(repo_root, chunk_files, i, extra_args)
        chunk_tasks.append(task)
    
    chunk_results = await asyncio.gather(*chunk_tasks)
    
    # Aggregate results
    final_result = aggregate_chunk_results(chunk_results)
    final_result["chunking_used"] = True
    final_result["chunk_count"] = len(chunks)
    
    # Cache successful results
    if use_cache and final_result["status"] == "ok":
        repo_path = Path(repo_root)
        all_test_paths = [repo_path / f for f in test_files]
        input_hash = ft_cache.sha256_of_paths(all_test_paths)
        
        ft_cache.write_tool_cache(
            repo_root, "pytest_parallel", input_hash, "ok",
            {
                "chunks": len(chunks),
                "files": len(test_files),
                "duration": final_result["total_duration"]
            }
        )
    
    return final_result


async def _run_single_pytest(
    repo_root: str, 
    test_files: List[str] | None,
    extra_args: List[str] | None = None
) -> Dict[str, Any]:
    """Run pytest normally (non-chunked) for small test suites"""
    
    cmd = ["python", "-m", "pytest", "-v", "--tb=short"]
    if extra_args:
        cmd.extend(extra_args)
    if test_files:
        cmd.extend(test_files)
    
    start_time = time.time()
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=repo_root,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )
        
        stdout, _ = await process.communicate()
        duration = time.time() - start_time
        
        return {
            "status": "ok" if process.returncode == 0 else "fail",
            "exit_code": process.returncode,
            "duration": duration,
            "output": stdout.decode('utf-8', 'replace'),
            "chunking_used": False,
            "file_count": len(test_files) if test_files else "all"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "duration": time.time() - start_time,
            "error": str(e),
            "output": f"Error running pytest: {e}",
            "chunking_used": False
        }