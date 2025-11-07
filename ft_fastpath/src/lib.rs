use anyhow::Result;
use crossbeam_channel as chan;
use ignore::{WalkBuilder, WalkState};
use pyo3::prelude::*;
use std::path::Path;
use std::time::{SystemTime, UNIX_EPOCH};

#[pyclass]
#[derive(Clone)]
pub struct FileEntry {
    #[pyo3(get)]
    pub path: String,
    #[pyo3(get)]
    pub size: u64,
    /// Seconds since UNIX epoch (0 if unknown)
    #[pyo3(get)]
    pub mtime_s: u64,
}

/// Scan a repository directory tree, respecting .gitignore/.ignore and git excludes.
/// Returns a list of files (not directories), each with path, size, and mtime.
/// `threads=0` lets the walker decide (usually #cores).
#[pyfunction]
pub fn scan_repo_parallel(
    py: Python<'_>,
    root_path: &str,
    threads: usize,
) -> PyResult<Vec<FileEntry>> {
    let root = Path::new(root_path);

    let entries = py.allow_threads(|| -> Vec<FileEntry> {
        let (tx, rx) = chan::unbounded::<FileEntry>();

        let mut builder = WalkBuilder::new(root);
        builder
            .hidden(false) // still respects .gitignore/.ignore
            .git_ignore(true)
            .git_exclude(true)
            .parents(true)
            .follow_links(false);

        if threads > 0 {
            builder.threads(threads);
        }

        // Parallel walker with a callback per entry
        builder.build_parallel().run(|| {
            let tx = tx.clone();
            Box::new(move |entry| {
                if let Ok(dirent) = entry {
                    if dirent
                        .file_type()
                        .map(|ft| ft.is_file())
                        .unwrap_or(false)
                    {
                        let (size, mtime_s) = match dirent.metadata() {
                            Ok(md) => {
                                let size = md.len();
                                let mtime_s = md
                                    .modified()
                                    .ok()
                                    .and_then(|t: SystemTime| {
                                        t.duration_since(UNIX_EPOCH).ok()
                                    })
                                    .map(|d| d.as_secs())
                                    .unwrap_or(0);
                                (size, mtime_s)
                            }
                            Err(_) => (0, 0),
                        };
                        let _ = tx.send(FileEntry {
                            path: dirent.path().to_string_lossy().to_string(),
                            size,
                            mtime_s,
                        });
                    }
                }
                WalkState::Continue
            })
        });

        drop(tx);
        let mut out = Vec::new();
        for fe in rx.iter() {
            out.push(fe);
        }
        out
    });

    Ok(entries)
}

#[pymodule]
fn ft_fastpath(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<FileEntry>()?;
    m.add_function(wrap_pyfunction!(scan_repo_parallel, m)?)?;
    Ok(())
}
