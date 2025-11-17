def test_all_ci_jobs_are_mapped():
    """Regresssion guard: ensure no CI jobs are left unmapped in the mirror."""
    from firsttry.ci_parity.checker import find_unmapped_ci_jobs

    unmapped = find_unmapped_ci_jobs()
    assert not unmapped, f"Found unmapped CI jobs: {[f'{j.workflow}:{j.job_id}' for j in unmapped]}"
