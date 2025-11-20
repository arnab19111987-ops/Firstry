def test_tools_firsttry_public_surface_matches_firsttry():
    import sys
    from pathlib import Path

    # Ensure project root is on sys.path so `tools` package can be imported reliably
    repo_root = Path.cwd()
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    import tools.firsttry as toolpkg

    import firsttry as mainpkg

    main_public = {n for n in dir(mainpkg) if not n.startswith("_")}
    tool_public = {n for n in dir(toolpkg) if not n.startswith("_")}

    missing = main_public - tool_public
    assert not missing, f"tools.firsttry missing attrs: {sorted(missing)}"
