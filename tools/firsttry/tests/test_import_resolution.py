import importlib.util
from pathlib import Path


def test_imports_tooling_package():
    # Load the inner tooling package's __init__.py directly so we avoid the
    # aliasing logic that points tools/firsttry -> repo root firsttry.
    here = Path(__file__).resolve()
    pkg_root = here.parents[1]  # tools/firsttry
    inner_init = pkg_root / "firsttry" / "__init__.py"

    spec = importlib.util.spec_from_file_location(
        "tooling_firsttry",
        str(inner_init),
        submodule_search_locations=[str(pkg_root / "firsttry")],
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # The __file__ should live under tools/firsttry/...
    assert "tools/firsttry" in str(Path(module.__file__).as_posix())
