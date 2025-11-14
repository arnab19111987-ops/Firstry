use pyo3::prelude::*;
use rayon::prelude::*;
use ignore::WalkBuilder;
use blake3::Hasher;
use std::fs;

#[pyfunction]
fn scan_repo_parallel(root: &str) -> PyResult<Vec<String>> {
    let mut files = Vec::new();
    WalkBuilder::new(root)
        .hidden(false)
        .follow_links(false)
        .build_parallel()
        .run(|| Box::new(move |result| {
            if let Ok(entry) = result {
                if entry.file_type().map(|ft| ft.is_file()).unwrap_or(false) {
                    if let Some(p) = entry.path().to_str() {
                        files.push(p.to_string());
                    }
                }
            }
            ignore::WalkState::Continue
        }));
    Ok(files)
}

#[pyfunction]
fn hash_files_parallel(paths: Vec<String>) -> PyResult<Vec<(String,String)>> {
    let out: Vec<(String,String)> = paths.par_iter().map(|p| {
        let data = fs::read(p).unwrap_or_default();
        let mut h = Hasher::new();
        h.update(&data);
        (p.clone(), h.finalize().to_hex().to_string())
    }).collect();
    Ok(out)
}

#[pymodule]
fn ft_fastpath(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(scan_repo_parallel, m)?)?;
    m.add_function(wrap_pyfunction!(hash_files_parallel, m)?)?;
    Ok(())
}
