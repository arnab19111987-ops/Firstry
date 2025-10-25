import json
from firsttry.doctor import run_doctor_report


def test_doctor_skip_all_marks_warning(monkeypatch):
    monkeypatch.setenv("FIRSTTRY_DOCTOR_SKIP", "all")
    rep = run_doctor_report(parallel=False)

    data = rep.to_dict()
    assert data["warning"] is not None
    assert "disabled" in data["warning"].lower()

    # all steps should be "skip"
    for item in data["results"]:
        assert item["status"] == "skip"
        assert "skipped due to FIRSTTRY_DOCTOR_SKIP=all" in item["detail"]

    # sanity: JSON round trip is valid
    js = rep.to_json()
    parsed = json.loads(js)
    assert parsed["warning"] == data["warning"]
