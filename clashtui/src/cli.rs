use clap::Parser;

/// sing-box TUI client
#[derive(Parser)]
#[command(version)]
pub struct Cmds {
    /// Use this directory for keymap/theme files instead of ~/.config/clashtui
    #[arg(long)]
    pub config_dir: Option<std::path::PathBuf>,
}

pub fn from_env() -> Cmds {
    let mut cmd = Cmds::parse();
    if cmd.config_dir.is_none() {
        cmd.config_dir = std::env::var_os("CLASHTUI_CONFIG_DIR").map(std::path::PathBuf::from);
    }
    cmd
}
