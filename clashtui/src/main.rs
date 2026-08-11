mod cli;
mod config;
mod functions;
mod tui;

fn main() {
    #[cfg(target_os = "linux")]
    nix::sys::stat::umask(nix::sys::stat::Mode::from_bits_truncate(0o002));

    let cmd = cli::from_env();
    if let Err(e) = config::init(cmd.config_dir) {
        eprintln!("Failed to init config dir\n{e}");
        return;
    }

    let log_path = config::config_dir_path().join("clashtui.log");
    let log_file = std::fs::OpenOptions::new()
        .create(true)
        .truncate(true)
        .write(true)
        .open(&log_path)
        .expect("Failed to open log file");
    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("warn"))
        .target(env_logger::Target::Pipe(Box::new(log_file)))
        .init();

    tui::init().unwrap();

    tui::App::serve().unwrap();

    tui::restore().unwrap();
}
