import xml.etree.ElementTree as ET
from pathlib import Path

from firsttry.ci_parity import monitor


def _j(path: Path, failures):
    testsuite = ET.Element("testsuite")
    for nid in failures:
        cls, _, name = nid.partition("::")
        tc = ET.SubElement(testsuite, "testcase", classname=cls or "", name=name or cls)
        ET.SubElement(tc, "failure")
    ET.ElementTree(testsuite).write(path)


def run_compare(warm, full):
    argv = ["monitor.py", str(warm), str(full)]
    try:
        monitor.main(argv)
        return 0
    except SystemExit as e:
        return int(e.code)


def test_pass_fail_exit99(tmp_path):
    w = tmp_path / "w.xml"
    f = tmp_path / "f.xml"
    _j(w, [])
    _j(f, ["x::y"])
    assert run_compare(w, f) == 99


def test_fail_pass_flaky_ok(tmp_path):
    w = tmp_path / "w.xml"
    f = tmp_path / "f.xml"
    _j(w, ["a::b"])
    _j(f, [])
    assert run_compare(w, f) == 0


def test_fail_fail_different_exit99(tmp_path):
    w = tmp_path / "w.xml"
    f = tmp_path / "f.xml"
    _j(w, ["a::b"])
    _j(f, ["c::d"])
    assert run_compare(w, f) == 99


def test_fail_fail_same_ok(tmp_path):
    w = tmp_path / "w.xml"
    f = tmp_path / "f.xml"
    _j(w, ["a::b"])
    _j(f, ["a::b"])
    assert run_compare(w, f) == 0
