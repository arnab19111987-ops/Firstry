from firsttry.env import DetectedEnv, detect_environment


def test_detect_environment_empty_repo(tmp_path):
    env = detect_environment(tmp_path)
    assert isinstance(env, DetectedEnv)
    assert env.has_python is False
    assert env.has_node is False
    assert env.has_go is False
    assert env.python_files == 0
    assert env.node_files == 0
    assert env.go_files == 0


def test_detect_environment_with_python(tmp_path):
    (tmp_path / "app.py").write_text("print('hi')")
    env = detect_environment(tmp_path)
    assert env.has_python is True
    assert env.python_files == 1
    assert env.to_pretty_json().startswith("{")
