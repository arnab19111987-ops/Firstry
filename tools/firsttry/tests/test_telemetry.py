
from firsttry import telemetry


def test_telemetry_respects_opt_out_and_opt_in(monkeypatch, tmp_path):
    # Point STATUS_FILE into tmpdir
    monkeypatch.setattr(telemetry, "STATUS_FILE", tmp_path / "telemetry_status.json")

    # Ensure no send when not opted in
    monkeypatch.delenv("FIRSTTRY_SEND_TELEMETRY", raising=False)
    monkeypatch.delenv("FIRSTTRY_TELEMETRY_OPTOUT", raising=False)
    monkeypatch.delenv("DO_NOT_TRACK", raising=False)

    telemetry.send_report({"foo": "bar"})  # should be a no-op
    assert not telemetry.STATUS_FILE.exists()

    # Opt-in
    monkeypatch.setenv("FIRSTTRY_SEND_TELEMETRY", "1")

    # Hard opt-out still wins
    monkeypatch.setenv("FIRSTTRY_TELEMETRY_OPTOUT", "1")
    telemetry.send_report({"foo": "bar"})
    assert not telemetry.STATUS_FILE.exists()

    # Remove opt-out; now it should at least attempt and write status (even if network fails)
    monkeypatch.setenv("FIRSTTRY_TELEMETRY_OPTOUT", "0")
    telemetry.send_report({"foo": "bar"})
    # We don't assert content, only that status file is touched as part of notify/write_status
    assert telemetry.STATUS_FILE.exists()
