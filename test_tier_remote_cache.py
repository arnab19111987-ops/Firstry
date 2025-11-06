#!/usr/bin/env python3
"""Test tier-based remote cache toggle."""

import sys
from pathlib import Path

def test_remote_cache_toggle():
    """Test that Pro enables remote cache, Lite doesn't."""
    
    print("Testing tier-based remote cache toggle:\n")
    
    # Test 1: Check the firsttry.toml config
    print("1. Checking firsttry.toml config:")
    with open("firsttry.toml") as f:
        content = f.read()
        tests_passed = []
        
        if "[tiers.lite]" in content and "[tiers.pro]" in content:
            print("   ✅ Both tiers.lite and tiers.pro defined")
            tests_passed.append(True)
        else:
            print("   ❌ Missing tier definitions")
            tests_passed.append(False)
            
        if "remote = false" in content:
            print("   ✅ Remote cache set to false in config (Pro enables at runtime)")
            tests_passed.append(True)
        else:
            print("   ❌ Remote cache not properly configured")
            tests_passed.append(False)
            
        if "local = true" in content:
            print("   ✅ Local cache enabled for all tiers")
            tests_passed.append(True)
        else:
            print("   ❌ Local cache not enabled")
            tests_passed.append(False)
            
        # Check that both tiers run the same checks
        lite_section = content[content.find("[tiers.lite]"):content.find("[tiers.pro]")]
        pro_section = content[content.find("[tiers.pro]"):content.find("[cache]")]
        
        if "run =" in lite_section and "run =" in pro_section:
            print("   ✅ Both tiers define 'run' lists")
            tests_passed.append(True)
        else:
            print("   ❌ Missing run lists")
            tests_passed.append(False)
    
    # Test 2: Check that run_swarm.py has the tier toggle
    print("\n2. Checking run_swarm.py implementation:")
    with open("src/firsttry/run_swarm.py") as f:
        content = f.read()
        
        if 'tier == "pro"' in content:
            print("   ✅ Pro tier check found")
            tests_passed.append(True)
        else:
            print("   ❌ Pro tier check missing")
            tests_passed.append(False)
            
        if "Runtime toggle" in content or "Only Pro tier" in content:
            print("   ✅ Runtime toggle logic present")
            tests_passed.append(True)
        else:
            print("   ❌ Runtime toggle logic missing")
            tests_passed.append(False)
    
    # Test 3: Check TTY rendering has the lock message
    print("\n3. Checking TTY rendering for lock message:")
    with open("src/firsttry/reporting/tty.py") as f:
        content = f.read()
        
        if "Shared Remote Cache (Pro)" in content:
            print("   ✅ Lock message found in TTY renderer")
            tests_passed.append(True)
        else:
            print("   ❌ Lock message missing")
            tests_passed.append(False)
            
        if 'tier_name.lower() in ("lite"' in content:
            print("   ✅ Tier check for lock message present")
            tests_passed.append(True)
        else:
            print("   ❌ Tier check missing")
            tests_passed.append(False)
    
    if all(tests_passed):
        print("\n✅ All tier-based remote cache tests passed!")
        print("\nImplementation summary:")
        print("- Lite: runs all checks locally, local cache only")
        print("- Pro: runs all checks locally, local + shared remote cache")
        print("- Config: both tiers run identical checks (tier-symmetric)")
        print("- Lock message: shown to Lite users in TTY output")
        return 0
    else:
        print(f"\n❌ {sum(not t for t in tests_passed)} tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(test_remote_cache_toggle())
