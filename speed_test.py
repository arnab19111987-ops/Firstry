#!/usr/bin/env python3
"""
FirstTry Speed Test Suite
Measures execution time for all FirstTry commands and options.
"""

import subprocess
import time
import json
import sys
from typing import Dict, List, Tuple, Any
from pathlib import Path

def run_command_with_timing(cmd: List[str], description: str, timeout: int = 60) -> Dict[str, Any]:
    """Run a command and measure its execution time."""
    print(f"Testing: {description}")
    print(f"Command: {' '.join(cmd)}")
    
    start_time = time.perf_counter()
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd="/workspaces/Firstry"
        )
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        return {
            "command": " ".join(cmd),
            "description": description,
            "duration_seconds": round(duration, 3),
            "exit_code": result.returncode,
            "stdout_lines": len(result.stdout.splitlines()),
            "stderr_lines": len(result.stderr.splitlines()),
            "success": result.returncode == 0,
            "stdout": result.stdout[:500] + "..." if len(result.stdout) > 500 else result.stdout,
            "stderr": result.stderr[:500] + "..." if len(result.stderr) > 500 else result.stderr,
        }
    except subprocess.TimeoutExpired:
        end_time = time.perf_counter()
        duration = end_time - start_time
        return {
            "command": " ".join(cmd),
            "description": description,
            "duration_seconds": round(duration, 3),
            "exit_code": -1,
            "stdout_lines": 0,
            "stderr_lines": 0,
            "success": False,
            "stdout": "",
            "stderr": f"Command timed out after {timeout} seconds",
            "timeout": True
        }
    except Exception as e:
        end_time = time.perf_counter()
        duration = end_time - start_time
        return {
            "command": " ".join(cmd),
            "description": description,
            "duration_seconds": round(duration, 3),
            "exit_code": -2,
            "stdout_lines": 0,
            "stderr_lines": 0,
            "success": False,
            "stdout": "",
            "stderr": f"Exception: {str(e)}",
            "exception": True
        }

def main():
    print("=" * 60)
    print("FirstTry Speed Test Suite")
    print("=" * 60)
    
    # Define all test cases
    test_cases = [
        # Basic commands
        (["python", "-m", "firsttry", "--help"], "Help command"),
        (["python", "-m", "firsttry", "version"], "Version command"),
        
        # Run command variations
        (["python", "-m", "firsttry", "run", "--help"], "Run help"),
        (["python", "-m", "firsttry", "run", "--tier", "developer"], "Run (developer tier)"),
        (["python", "-m", "firsttry", "run", "--tier", "teams"], "Run (teams tier)"),
        (["python", "-m", "firsttry", "run", "--profile", "fast"], "Run (fast profile)"),
        (["python", "-m", "firsttry", "run", "--profile", "strict"], "Run (strict profile)"),
        (["python", "-m", "firsttry", "run", "--source", "detect"], "Run (detect source)"),
        (["python", "-m", "firsttry", "run", "--source", "config"], "Run (config source)"),
        (["python", "-m", "firsttry", "run", "--source", "ci"], "Run (CI source)"),
        
        # Other commands
        (["python", "-m", "firsttry", "inspect"], "Inspect command"),
        (["python", "-m", "firsttry", "sync"], "Sync command"),
        (["python", "-m", "firsttry", "status"], "Status command"),
        (["python", "-m", "firsttry", "setup"], "Setup command"),
        (["python", "-m", "firsttry", "doctor"], "Doctor command"),
        (["python", "-m", "firsttry", "mirror-ci"], "Mirror-CI command"),
        (["python", "-m", "firsttry", "mirror-ci", "--help"], "Mirror-CI help"),
    ]
    
    results = []
    total_start = time.perf_counter()
    
    for i, (cmd, desc) in enumerate(test_cases, 1):
        print(f"\n[{i}/{len(test_cases)}] ", end="")
        result = run_command_with_timing(cmd, desc, timeout=120)
        results.append(result)
        
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        print(f"  → {result['duration_seconds']}s {status}")
        
        # Add a small delay between commands to avoid overwhelming the system
        time.sleep(0.5)
    
    total_end = time.perf_counter()
    total_duration = total_end - total_start
    
    # Generate detailed report
    print("\n" + "=" * 60)
    print("DETAILED SPEED TEST REPORT")
    print("=" * 60)
    
    # Summary statistics
    successful_tests = [r for r in results if r["success"]]
    failed_tests = [r for r in results if not r["success"]]
    durations = [r["duration_seconds"] for r in results]
    
    print(f"\n📊 SUMMARY STATISTICS:")
    print(f"  Total Tests:       {len(results)}")
    print(f"  Successful:        {len(successful_tests)} ({len(successful_tests)/len(results)*100:.1f}%)")
    print(f"  Failed:            {len(failed_tests)} ({len(failed_tests)/len(results)*100:.1f}%)")
    print(f"  Total Runtime:     {total_duration:.3f}s")
    print(f"  Average Duration:  {sum(durations)/len(durations):.3f}s")
    print(f"  Fastest Command:   {min(durations):.3f}s")
    print(f"  Slowest Command:   {max(durations):.3f}s")
    
    # Performance breakdown
    print(f"\n⚡ PERFORMANCE BREAKDOWN:")
    sorted_results = sorted(results, key=lambda x: x["duration_seconds"])
    
    for result in sorted_results:
        status_icon = "✅" if result["success"] else "❌"
        print(f"  {result['duration_seconds']:6.3f}s {status_icon} {result['description']}")
    
    # Command categories analysis
    run_commands = [r for r in results if "run" in r["command"].lower() and "--help" not in r["command"]]
    help_commands = [r for r in results if "--help" in r["command"]]
    other_commands = [r for r in results if r not in run_commands and r not in help_commands]
    
    print(f"\n📈 CATEGORY ANALYSIS:")
    if run_commands:
        run_avg = sum(r["duration_seconds"] for r in run_commands) / len(run_commands)
        print(f"  Run Commands:      {len(run_commands)} tests, avg {run_avg:.3f}s")
    
    if help_commands:
        help_avg = sum(r["duration_seconds"] for r in help_commands) / len(help_commands)
        print(f"  Help Commands:     {len(help_commands)} tests, avg {help_avg:.3f}s")
    
    if other_commands:
        other_avg = sum(r["duration_seconds"] for r in other_commands) / len(other_commands)
        print(f"  Other Commands:    {len(other_commands)} tests, avg {other_avg:.3f}s")
    
    # Bucketed execution analysis
    bucketed_commands = [r for r in results if "run" in r["command"] and "tier" in r["command"]]
    if bucketed_commands:
        print(f"\n🪣 BUCKETED EXECUTION ANALYSIS:")
        for result in bucketed_commands:
            phases = []
            if "⚡ firsttry: running FAST" in result["stdout"]:
                phases.append("FAST")
            if "→ firsttry: running MUTATING" in result["stdout"]:
                phases.append("MUTATING")  
            if "⏳ firsttry: running SLOW" in result["stdout"]:
                phases.append("SLOW")
            
            phase_str = " → ".join(phases) if phases else "No phases detected"
            print(f"  {result['duration_seconds']:6.3f}s {result['description']}: {phase_str}")
    
    # Failure analysis
    if failed_tests:
        print(f"\n❌ FAILURE ANALYSIS:")
        for result in failed_tests:
            print(f"  • {result['description']}: {result['stderr'][:100]}...")
    
    # Performance recommendations
    print(f"\n💡 PERFORMANCE INSIGHTS:")
    
    fastest = min(results, key=lambda x: x["duration_seconds"])
    slowest = max(results, key=lambda x: x["duration_seconds"])
    
    print(f"  • Fastest: {fastest['description']} ({fastest['duration_seconds']}s)")
    print(f"  • Slowest: {slowest['description']} ({slowest['duration_seconds']}s)")
    
    if run_commands:
        run_durations = [r["duration_seconds"] for r in run_commands]
        if max(run_durations) > 10:
            print(f"  • Long-running commands detected (>{10}s). Consider optimizing check execution.")
        if len([d for d in run_durations if d < 1]) > 0:
            print(f"  • Fast commands detected (<1s). Good responsiveness for quick feedback.")
    
    print(f"\n📋 DETAILED RESULTS:")
    for result in results:
        print(f"\n  Command: {result['command']}")
        print(f"  Duration: {result['duration_seconds']}s")
        print(f"  Exit Code: {result['exit_code']}")
        print(f"  Success: {result['success']}")
        if result.get('timeout'):
            print(f"  Status: TIMEOUT")
        elif result.get('exception'):
            print(f"  Status: EXCEPTION")
        if result['stderr'] and not result['success']:
            print(f"  Error: {result['stderr'][:200]}...")
    
    # Save detailed results to JSON
    with open('/workspaces/Firstry/speed_test_results.json', 'w') as f:
        json.dump({
            'summary': {
                'total_tests': len(results),
                'successful_tests': len(successful_tests),
                'failed_tests': len(failed_tests),
                'total_duration': total_duration,
                'average_duration': sum(durations)/len(durations),
                'fastest_duration': min(durations),
                'slowest_duration': max(durations),
            },
            'results': results
        }, f, indent=2)
    
    print(f"\n📁 Detailed results saved to: speed_test_results.json")
    print("=" * 60)

if __name__ == "__main__":
    main()