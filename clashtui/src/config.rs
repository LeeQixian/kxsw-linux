use anyhow::{Context, Result};
use std::path::PathBuf;
use std::sync::OnceLock;
use util::*;

#[macro_use]
mod util;

static DATA_DIR: OnceLock<PathBuf> = OnceLock::new();

pub const API_ADDR: &str = "http://127.0.0.1:9090";
pub const API_SECRET: Option<&str> = None;
pub const API_TIMEOUT: u64 = 5;

pub fn init(base_path: Option<PathBuf>) -> Result<()> {
    let dir = match base_path {
        Some(p) => p,
        None => load_home_dir()?,
    };
    DATA_DIR
        .set(dir)
        .map_err(|_| anyhow::anyhow!("config initialized twice"))?;
    std::fs::create_dir_all(config_dir_path())
        .context("Failed to create config dir")?;
    Ok(())
}

pub fn config_dir_path() -> PathBuf {
    DATA_DIR.get().expect("config not initialized").clone()
}

pub fn keymap_path() -> PathBuf {
    config_dir_path().join(defs::KEYMAP_FILE)
}

pub fn theme_path() -> PathBuf {
    config_dir_path().join(defs::THEME_FILE)
}
