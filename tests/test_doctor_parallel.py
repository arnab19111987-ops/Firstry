import json
from typing import List

import firsttry.doctor as doc


class FakeRunner:
    def run(self, cmd: List[str]):
        # Make mypy fail to trigger quickfix; others pass
        if cmd and cmd[0] == "mypy":
            return 1, "mypy: error: Something bad"
        return 0, "ok"


def test_gather_checks_parallel_and_quickfix():
    report = doc.gather_checks(runner=FakeRunner(), parallel=True)
    assert report.total_count >= 5
    assert report.passed_count < report.total_count
    # Expect a mypy quickfix suggestion
    joined = "\n".join(report.quickfixes)
    assert "Mypy type errors" in joined

    # JSON round-trip
    js = doc.render_report_json(report)
    data = json.loads(js)
    assert data["total_count"] == report.total_count
    assert (
        data["summary"].startswith(str(report.passed_count))
        if isinstance(data.get("summary"), str)
        else True
    )
