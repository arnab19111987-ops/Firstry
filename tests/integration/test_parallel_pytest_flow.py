import asyncio
from types import SimpleNamespace

import firsttry.parallel_pytest as pp


def test_parallel_pytest_happy_path(monkeypatch, tmp_path):
    # Create a modest number of test files to encourage chunking
    for i in range(12):
        (tmp_path / f"test_{i}.py").write_text(f"def test_{i}():\n    assert True\n", encoding="utf-8")

    # Fake run_pytest_chunk to avoid spawning subprocesses
    async def fake_run_pytest_chunk(repo_root, chunk_files, chunk_id, extra_args=None):
        return {
            "chunk_id": chunk_id,
            "status": "ok",
            "exit_code": 0,
            "files": chunk_files,
            "file_count": len(chunk_files),
            "duration": 0.01,
            "output": "OK",
        }

    monkeypatch.setattr(pp, "run_pytest_chunk", fake_run_pytest_chunk)

    # Also monkeypatch cache checks to avoid hashing
    monkeypatch.setattr(pp.ft_cache, "is_tool_cache_valid", lambda *a, **k: False)
    monkeypatch.setattr(pp.ft_cache, "sha256_of_paths", lambda *a, **k: "deadbeef")
    monkeypatch.setattr(pp.ft_cache, "write_tool_cache", lambda *a, **k: None)

    # Execute parallel runner - pass explicit test_files to force chunking
    test_files = [p.name for p in tmp_path.glob("test_*.py")]
    result = asyncio.run(pp.run_parallel_pytest(str(tmp_path), test_files=test_files, max_workers=2))

    assert result["status"] == "ok"
    assert result.get("chunking_used") is True
    assert result.get("chunk_count", 0) >= 2
