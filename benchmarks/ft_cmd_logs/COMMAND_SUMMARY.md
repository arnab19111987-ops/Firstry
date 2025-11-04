## 20251104-060706_ft_--help.log

PREVIEW:
=== Running: ft --help
Usage: ft <command> [options]

Core fast flows:
  ft lite
      -> python -m firsttry run fast --tier free-lite --profile fast --report-json .firsttry/report.json

KEYS:
-> python -m firsttry inspect report --json .firsttry/report.json --filter locked=true

---

## 20251104-060707_ft_version.log

PREVIEW:
=== Running: ft version
FirstTry 0.1.0
Usage: ft <command> [options]

Core fast flows:
  ft lite

KEYS:
-> python -m firsttry inspect report --json .firsttry/report.json --filter locked=true

---

## 20251104-060708_ft_lite_--report-json_.firsttry_free-lite.ent.json_--show-report.log

PREVIEW:
=== Running: ft lite --report-json .firsttry/free-lite.ent.json --show-report

⏱️  Time split:
  fast: 3.3s (mypy=3.3s, ruff=0.0s)
  slow: 2.8s (pytest=2.8s, ci-parity=0.0s)
  other: 2.6s (pip-audit=2.6s, bandit=0.0s)

KEYS:
[93mmypy[0m: 🔒 Locked — available in Pro / ProMax. Run `firsttry upgrade` to unlock.
[93mpytest[0m: 🔒 Locked — available in Pro / ProMax. Run `firsttry upgrade` to unlock.
[93mbandit[0m: 🔒 Locked — available in Pro / ProMax. Run `firsttry upgrade` to unlock.
[93mpip-audit[0m: 🔒 Locked — available in Pro / ProMax. Run `firsttry upgrade` to unlock.
[93mci-parity[0m: 🔒 Locked — available in Pro / ProMax. Run `firsttry upgrade` to unlock.

---

## 20251104-060713_ft_strict_--report-json_.firsttry_free-strict.ent.json_--show-report.log

PREVIEW:
=== Running: ft strict --report-json .firsttry/free-strict.ent.json --show-report

⏱️  Time split:
  fast: 3.3s (mypy=3.3s, ruff=0.0s)
  slow: 2.8s (pytest=2.8s, ci-parity=0.1s)
  other: 2.6s (pip-audit=2.6s, bandit=0.0s)

KEYS:
[92m✅[0m [1mmypy[0m: benchmarks/repos/repo-a-no-config/tests/test_utils1.py:1: error: invalid syntax  [syntax]
[92m✅[0m [1mpytest[0m: ==================================== ERRORS ====================================
[93mbandit[0m: 🔒 Locked — available in Pro / ProMax. Run `firsttry upgrade` to unlock.
[93mpip-audit[0m: 🔒 Locked — available in Pro / ProMax. Run `firsttry upgrade` to unlock.
[93mci-parity[0m: 🔒 Locked — available in Pro / ProMax. Run `firsttry upgrade` to unlock.

---

## 20251104-060717_ft_pro_--report-json_.firsttry_pro.ent.json_--show-report.log

PREVIEW:
=== Running: ft pro --report-json .firsttry/pro.ent.json --show-report
❌ Tier 'pro' is locked. Set FIRSTTRY_LICENSE_KEY=... or run `firsttry license activate`.
💡 Get a license at https://firsttry.com/pricing

KEYS:
❌ Tier 'pro' is locked. Set FIRSTTRY_LICENSE_KEY=... or run `firsttry license activate`.

---

## 20251104-060719_ft_promax_--report-json_.firsttry_promax.ent.json_--show-report.log

PREVIEW:
=== Running: ft promax --report-json .firsttry/promax.ent.json --show-report
Usage: ft <command> [options]

Core fast flows:
  ft lite
      -> python -m firsttry run fast --tier free-lite --profile fast --report-json .firsttry/report.json

KEYS:
-> python -m firsttry inspect report --json .firsttry/report.json --filter locked=true

---

## 20251104-060720_ft_doctor_--tools.log

PREVIEW:
=== Running: ft doctor --tools
ruff: ok
mypy: ok
pytest: ok
node: missing
npm: missing

KEYS:
node: missing
npm: missing

---

## 20251104-060721_ft_doctor_--check_report-json_--check_telemetry.log

PREVIEW:
=== Running: ft doctor --check report-json --check telemetry
Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "/workspaces/Firstry/src/firsttry/__main__.py", line 7, in <module>
    raise SystemExit(main())

KEYS:
Traceback (most recent call last):
KeyboardInterrupt
Traceback (most recent call last):
KeyboardInterrupt

---
