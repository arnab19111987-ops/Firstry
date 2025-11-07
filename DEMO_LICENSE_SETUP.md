# Demo License Setup Guide

Universal demo pre-license key valid for every test in the FirstTry project.

## Quick Start

### Bash/Shell

```bash
# Enable demo license for all tests
source demo_license_setup.sh

# Specify tier
source demo_license_setup.sh pro        # Pro tier (default)
source demo_license_setup.sh promax     # ProMax tier
source demo_license_setup.sh free-lite  # Free Lite (no license needed)

# Now run tests with license
pytest tests/
firsttry run --tier pro
```

### Python (Direct)

```python
from demo_license_for_tests import setup_demo_license, DemoLicense

# Enable for entire session
setup_demo_license(tier="pro")

# Or use as context manager
with DemoLicense(tier="pro"):
    # Tests here will use demo license
    pytest.main([...])
```

### pytest (conftest.py)

```python
# conftest.py already configured with demo license
# No additional setup needed - tests run with demo license automatically

# Or customize in specific test:
from demo_license_for_tests import DemoLicense

def test_pro_features():
    with DemoLicense(tier="pro"):
        # This test runs with pro tier demo license
        assert firsttry_command()
```

## Demo License Details

```
Key:     demo-lic-key-2025
Backend: env (environment variable based)
Tiers:   pro, promax, free-lite, free-strict
Status:  Valid for all tests ✓
```

## Environment Variables

When demo license is enabled:

```bash
FIRSTTRY_LICENSE_KEY="demo-lic-key-2025"
FIRSTTRY_LICENSE_BACKEND="env"
FIRSTTRY_LICENSE_ALLOW="pro,promax"
FIRSTTRY_TIER="pro"  # Default tier
```

## Supported Tier Aliases

### Pro Tier (Paid)
- `pro`
- `team`
- `teams`
- `full`

### ProMax Tier (Paid)
- `promax`
- `enterprise`
- `org`

### Free Lite Tier
- `free-lite`
- `free`
- `lite`
- `dev`
- `developer`
- `fast`
- `auto`

### Free Strict Tier
- `free-strict`
- `strict`
- `ci`
- `config`
- `verify`

## Usage Examples

### Example 1: Test Pro Features

```bash
# Enable demo license
source demo_license_setup.sh pro

# Run tests
pytest tests/test_pro_features.py -v
```

### Example 2: Test Multiple Tiers

```bash
# Test pro tier
source demo_license_setup.sh pro
pytest tests/

# Test promax tier
source demo_license_setup.sh promax
pytest tests/

# Test free tier (no license)
source demo_license_setup.sh free-lite
pytest tests/
```

### Example 3: Python Test

```python
import pytest
from demo_license_for_tests import DemoLicense

class TestProFeatures:
    def test_with_demo_license(self):
        """Test with demo license enabled."""
        with DemoLicense(tier="pro"):
            from firsttry import license_guard
            assert license_guard.is_pro()
            assert license_guard.get_tier() == "pro"

    def test_with_promax(self):
        """Test with promax tier."""
        with DemoLicense(tier="promax"):
            from firsttry import license_guard
            assert license_guard.get_tier() == "promax"
```

### Example 4: CI/CD (GitHub Actions)

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
      - name: Install dependencies
        run: pip install -e .[dev]
      - name: Enable demo license
        run: source demo_license_setup.sh pro
      - name: Run tests
        run: pytest tests/
```

### Example 5: CLI Testing

```bash
# Enable demo license
source demo_license_setup.sh pro

# Test pro tier features
firsttry run --tier pro --gate pre-commit

# Test with uploaded benchmarks
python tools/ft_bench_harness.py --upload-s3 --tier pro
```

## How It Works

The demo license system uses an **ENV backend** for validation:

1. **conftest.py** automatically sets environment variables
2. **license_guard.py** checks `FIRSTTRY_LICENSE_BACKEND=env`
3. **license_cache.py** validates via ENV backend (always succeeds if tier is in ALLOW list)
4. **Tests run** without hitting remote license server

### Validation Flow

```
Test starts
  ↓
license_guard.ensure_license_for_current_tier()
  ↓
_validate_license_max_security(key="demo-lic-key-2025", tier="pro")
  ↓
license_cache.validate_license_key(key, tier)
  ↓
Backend="env" check:
  - FIRSTTRY_LICENSE_KEY exists? ✓ (demo-lic-key-2025)
  - FIRSTTRY_LICENSE_ALLOW contains tier? ✓ (pro in "pro,promax")
  ↓
Returns True
  ↓
Test continues ✓
```

## Disabling Demo License

### Bash

```bash
# Unset all demo license environment variables
unset FIRSTTRY_LICENSE_KEY
unset FIRSTTRY_TIER
unset FIRSTTRY_LICENSE_BACKEND
unset FIRSTTRY_LICENSE_ALLOW

# Or disable in new shell
exec bash  # Fresh shell without demo license
```

### Python

```python
from demo_license_for_tests import DemoLicense

# Use context manager - auto-restores on exit
with DemoLicense(tier="pro"):
    # License enabled here
    pass
# License disabled here

# Or manually restore
license = DemoLicense(tier="pro")
license.enable()
# ... do something ...
license.disable()
```

## Testing the Demo License

### Verify License Is Working

```bash
source demo_license_setup.sh pro

# Test 1: Check environment
echo $FIRSTTRY_LICENSE_KEY
echo $FIRSTTRY_TIER

# Test 2: Python validation
python -c "from firsttry.license_guard import is_pro; print(is_pro())"
# Should print: True

# Test 3: Run test that requires license
pytest tests/test_cli_run.py -v
```

### Verify LICENSE_ALLOW Restriction

```bash
# This should work (pro in ALLOW list)
FIRSTTRY_TIER=pro python -c "from firsttry.license_guard import ensure_license_for_current_tier; ensure_license_for_current_tier()"
# Success ✓

# This would fail (lite not in ALLOW list) if we didn't allow it
# (demo license allows pro and promax by default)
```

## Advanced: Custom Demo Licenses

You can create additional demo licenses by modifying environment variables:

```bash
# Custom test license
export FIRSTTRY_LICENSE_KEY="my-test-key-12345"
export FIRSTTRY_LICENSE_BACKEND="env"
export FIRSTTRY_LICENSE_ALLOW="pro,promax,free-lite"
export FIRSTTRY_TIER="pro"

# Now tests use your custom key
pytest tests/
```

## Troubleshooting

### "License not valid for tier" Error

**Problem:** License validation fails in tests

**Solution:**
```bash
# Verify demo license is enabled
source demo_license_setup.sh pro

# Check environment variables
env | grep FIRSTTRY

# Re-enable fresh
unset FIRSTTRY_LICENSE_KEY FIRSTTRY_TIER FIRSTTRY_LICENSE_BACKEND FIRSTTRY_LICENSE_ALLOW
source demo_license_setup.sh pro
```

### License Backend Not Found

**Problem:** "Unknown license backend" error

**Solution:**
- Verify `FIRSTTRY_LICENSE_BACKEND=env` is set
- Check that `license_cache.py` exists in `src/firsttry/`
- Verify ENV backend is implemented (it is by default)

### Tests Still Require License

**Problem:** Tests run but still hit license check

**Solution:**
- Check if tests are run in subprocess (need to pass env)
- Verify `conftest.py` demo license setup runs first
- Use `DemoLicense` context manager for subprocess tests

### Pro Tier Not Detected

**Problem:** `is_pro()` returns False

**Solution:**
```bash
# Verify tier is set
echo $FIRSTTRY_TIER  # Should print: pro

# Verify it matches canonical name
export FIRSTTRY_TIER="pro"  # Use canonical form

# If using alias, ensure it's in TIER_SYNONYMS in license_guard.py
```

## Security Notes

⚠️ **Important:** The demo license is for **testing only**.

- ✅ Safe: Use in local development and testing
- ✅ Safe: Use in CI/CD pipelines for automated tests
- ❌ Unsafe: Use in production
- ❌ Unsafe: Commit production license keys
- ❌ Unsafe: Use demo key for actual paid features

## Files Included

1. **demo_license_setup.sh** - Bash script to enable demo license
2. **demo_license_for_tests.py** - Python module with DemoLicense class
3. **DEMO_LICENSE_SETUP.md** - This documentation
4. **conftest.py** - Updated to auto-enable demo license

## Integration Points

The demo license integrates seamlessly with:

- ✅ pytest (auto-enabled via conftest.py)
- ✅ GitHub Actions workflows
- ✅ GitLab CI pipelines
- ✅ Local development shell
- ✅ Docker containers
- ✅ Pre-commit hooks

## Version

- **Demo License Key:** `demo-lic-key-2025`
- **Backend:** ENV (environment-based validation)
- **Status:** Valid for all FirstTry tests ✓
- **Created:** 2025-11-07

---

For questions or issues, check the [FirstTry License Documentation](./LICENSE.md).
