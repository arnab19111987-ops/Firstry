import pytest

try:
    import firsttry.ft_fastpath as ff
except Exception:
    ff = None
import blake3


@pytest.mark.skipif(ff is None, reason="Rust fastpath not present")
def test_hashes_match_python_fallback(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("abc")
    rust = dict(ff.hash_files_parallel([str(p)]))
    py = blake3.blake3(p.read_bytes()).hexdigest()
    assert rust[str(p)] == py
