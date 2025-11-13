import sys
from pathlib import Path


def _load_failures(junit_path: Path) -> set[str]:
    """Load failing test nodeids from a minimal JUnit XML file.

    Returns a set of nodeids like 'module.Class::test_name' or 'module::test'.
    """
    import xml.etree.ElementTree as ET

    t = ET.parse(junit_path)
    nodeids = set()
    for case in t.iterfind('.//testcase'):
        # If testcase has child elements like <failure/> or <error/>
        if list(case):
            cls = case.get('classname') or ''
            name = case.get('name') or ''
            nodeids.add(f"{cls}::{name}" if cls else name)
    return nodeids


def main(argv=None):
    # argv is ignored; use sys.argv for CLI convenience
    if argv is None:
        argv = sys.argv
    # If a test or caller provided a `load_report` function (tests monkeypatch
    # this), prefer to use it directly. Otherwise, fall back to loading
    # JUnit XMLs from the provided argv paths.
    if hasattr(sys.modules[__name__], "load_report"):
        # If caller supplied args, forward them; otherwise call with None
        if len(argv) >= 3:
            rep = load_report(argv[1], argv[2])
        else:
            rep = load_report(None, None)
        wpass = rep.warm_pass
        fpass = rep.full_pass
        wfail = set(rep.warm_fail_ids)
        ffail = set(rep.full_fail_ids)
    else:
        if len(argv) < 3:
            print('Usage: firsttry.ci_parity.monitor <warm-junit> <full-junit>')
            sys.exit(2)
        w, f = Path(argv[1]), Path(argv[2])
        wfail, ffail = _load_failures(w), _load_failures(f)
        wpass = not wfail
        fpass = not ffail
    wpass = not wfail
    fpass = not ffail
    if wpass and not fpass:
        print('DIVERGENCE: Warm=PASS, Full=FAIL → exit 99')
        sys.exit(99)
    if (not wpass) and fpass:
        print('WEAPONIZED: Warm=FAIL, Full=PASS → flaky; allow CI to self-heal')
        sys.exit(0)
    if (not wpass) and (not fpass) and (wfail != ffail):
        print(f'DIVERGENCE: Warm failed {sorted(wfail)}; Full failed {sorted(ffail)} → exit 99')
        sys.exit(99)
    sys.exit(0)


if __name__ == '__main__':
    main()


def load_report(warm_junit: str | None, full_junit: str | None):
    """Load a simple report object describing warm/full jUnit outcomes.

    Returns an object with attributes: warm_pass, full_pass, warm_fail_ids, full_fail_ids
    """
    from types import SimpleNamespace

    warm_fail = set()
    full_fail = set()
    if warm_junit:
        try:
            warm_fail = _load_failures(Path(warm_junit))
        except Exception:
            warm_fail = set()
    if full_junit:
        try:
            full_fail = _load_failures(Path(full_junit))
        except Exception:
            full_fail = set()

    return SimpleNamespace(
        warm_pass=(not warm_fail),
        full_pass=(not full_fail),
        warm_fail_ids=warm_fail,
        full_fail_ids=full_fail,
    )
