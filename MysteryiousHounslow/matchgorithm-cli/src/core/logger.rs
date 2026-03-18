use tracing_subscriber::{fmt, EnvFilter};
use chrono::Local;

pub fn init() {
    let timer = fmt::time::UtcTime::new(Local::now().format("%Y-%m-%d %H:%M:%S%.3f").to_string());

    fmt()
        .with_env_filter(EnvFilter::from_default_env())
        .with_timer(timer)
        .with_target(false)
        .init();
}