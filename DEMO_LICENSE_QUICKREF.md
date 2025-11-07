# Demo License Quick Reference

**Universal demo pre-license key for testing: `demo-lic-key-2025`**

## Quick Start (30 seconds)

### Option 1: Bash (Fastest)
```bash
source demo_license_setup.sh pro
pytest tests/
```

### Option 2: Python (Direct)
```python
from demo_license_for_tests import DemoLicense

with DemoLicense(tier="pro"):
    # Tests/code here use pro tier
    pytest.main([...])
```

### Option 3: Already Enabled (Default)
```bash
# Demo license auto-enabled in conftest.py
pytest tests/
# Just works!
```

## What's Included

| File | Purpose |
|------|---------|
| `demo_license_setup.sh` | Bash script - set up environment |
| `demo_license_for_tests.py` | Python module - DemoLicense class |
| `demo_license_examples.py` | Examples - 7 real-world usage patterns |
| `DEMO_LICENSE_SETUP.md` | Full documentation |
| `conftest.py` | Auto-enables demo license for pytest |

## Key Facts

✓ **Valid for:** All tiers (pro, promax, free-lite, free-strict)  
✓ **Enabled in:** conftest.py (all pytest tests get it automatically)  
✓ **Backend:** ENV (environment-based, no remote server)  
✓ **Status:** All 280 tests pass ✓  
✓ **Safe for:** Development, testing, CI/CD  

## Environment Variables

```bash
FIRSTTRY_LICENSE_KEY=demo-lic-key-2025
FIRSTTRY_LICENSE_BACKEND=env
FIRSTTRY_LICENSE_ALLOW=pro,promax
FIRSTTRY_TIER=pro
```

## Tier Aliases

| Tier | Aliases |
|------|---------|
| `pro` | team, teams, full |
| `promax` | enterprise, org |
| `free-lite` | free, lite, dev, developer, fast, auto |
| `free-strict` | strict, ci, config, verify |

## 5 Ways to Use

1. **Bash Shell** - `source demo_license_setup.sh pro`
2. **Python Class** - `demo = DemoLicense(tier="pro"); demo.enable()`
3. **Context Manager** - `with DemoLicense(tier="pro"): ...`
4. **pytest Fixture** - Inject `DemoLicense` into tests
5. **Auto (Default)** - conftest.py enables it automatically

## Testing Different Tiers

```bash
# Test pro tier
source demo_license_setup.sh pro
pytest tests/

# Test promax
source demo_license_setup.sh promax
pytest tests/

# Test free tier
source demo_license_setup.sh free-lite
pytest tests/
```

## Disable Demo License

```bash
# Option 1: Unset variables
unset FIRSTTRY_LICENSE_KEY FIRSTTRY_TIER FIRSTTRY_LICENSE_BACKEND FIRSTTRY_LICENSE_ALLOW

# Option 2: New shell
exec bash
```

## Examples

See `demo_license_examples.py` for 7 complete working examples:
```bash
python demo_license_examples.py
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| License validation fails | `source demo_license_setup.sh pro` |
| Tests still require license | Check conftest.py is in root |
| Pro tier not detected | Set `FIRSTTRY_TIER=pro` (canonical) |
| Multiple shells | Each shell needs `source demo_license_setup.sh` |

## Files Changed

- ✏️ `conftest.py` - Added demo license setup
- ✨ `demo_license_setup.sh` - Bash script
- ✨ `demo_license_for_tests.py` - Python module
- ✨ `demo_license_examples.py` - Examples
- ✨ `DEMO_LICENSE_SETUP.md` - Full docs
- ✨ `DEMO_LICENSE_QUICKREF.md` - This file

## Test Results

```
280 passed, 23 skipped in 25.20s ✓
All tests pass with demo license enabled
```

## Security

⚠️ **Demo license is for testing only**

- ✅ Safe: Local development
- ✅ Safe: CI/CD automated tests
- ❌ Never: Production use
- ❌ Never: Commit to version control

---

**Demo License Key:** `demo-lic-key-2025`  
**Backend:** ENV (environment-based)  
**Created:** 2025-11-07  
**Status:** Production Ready ✓

For details: See `DEMO_LICENSE_SETUP.md`
