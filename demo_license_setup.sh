#!/bin/bash
# demo_license_setup.sh
# Demo pre-license setup for testing - valid for all tests
# This sets up a working demo license environment for development and testing

# Usage:
#   source demo_license_setup.sh           # Enable demo license
#   source demo_license_setup.sh pro       # Enable pro tier with demo license
#   source demo_license_setup.sh teams     # Enable teams tier with demo license
#   source demo_license_setup.sh promax    # Enable promax tier with demo license
#   unset FIRSTTRY_LICENSE_KEY             # Disable demo license

set -e

# Demo license key - valid for all tiers and tests
export FIRSTTRY_LICENSE_KEY="demo-lic-key-2025"

# Default tier (can be overridden by argument)
TIER="${1:-pro}"

# Normalize tier
case "${TIER,,}" in
  pro|team|teams|full)
    export FIRSTTRY_TIER="pro"
    echo "[demo-license] ✓ Pro tier enabled with demo license key"
    ;;
  promax|enterprise|org)
    export FIRSTTRY_TIER="promax"
    echo "[demo-license] ✓ ProMax tier enabled with demo license key"
    ;;
  free|free-lite|lite|dev|developer|fast|auto)
    export FIRSTTRY_TIER="free-lite"
    echo "[demo-license] ✓ Free Lite tier enabled (no license needed)"
    ;;
  free-strict|strict|ci|config|verify)
    export FIRSTTRY_TIER="free-strict"
    echo "[demo-license] ✓ Free Strict tier enabled (no license needed)"
    ;;
  *)
    export FIRSTTRY_TIER="pro"
    echo "[demo-license] ✓ Pro tier enabled with demo license key (default)"
    ;;
esac

# Show current environment
echo "[demo-license] Environment:"
echo "  FIRSTTRY_LICENSE_KEY=${FIRSTTRY_LICENSE_KEY}"
echo "  FIRSTTRY_TIER=${FIRSTTRY_TIER}"
echo ""
echo "[demo-license] ENV backend configured:"
export FIRSTTRY_LICENSE_BACKEND="env"
export FIRSTTRY_LICENSE_ALLOW="${FIRSTTRY_TIER},pro,promax"
echo "  FIRSTTRY_LICENSE_BACKEND=${FIRSTTRY_LICENSE_BACKEND}"
echo "  FIRSTTRY_LICENSE_ALLOW=${FIRSTTRY_LICENSE_ALLOW}"
echo ""
echo "[demo-license] To test with different tiers:"
echo "  source demo_license_setup.sh pro        # Pro tier"
echo "  source demo_license_setup.sh promax     # ProMax tier"
echo "  source demo_license_setup.sh free-lite  # Free Lite tier"
echo ""
echo "[demo-license] To disable demo license:"
echo "  unset FIRSTTRY_LICENSE_KEY"
echo "  unset FIRSTTRY_TIER"
echo "  unset FIRSTTRY_LICENSE_BACKEND"
echo "  unset FIRSTTRY_LICENSE_ALLOW"
