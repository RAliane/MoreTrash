//! Page components for Dioxus SSR
//!
//! Each page corresponds to a route defined in main.rs.
//! Pages are server-rendered and hydrated on the client.

pub mod about;
pub mod auth;
pub mod contact;
pub mod dashboard;
pub mod home;
pub mod platform;
pub mod pricing;
pub mod solutions;

// Re-export page components
pub use about::About;
pub use auth::{ForgotPassword, ResetPassword, SignIn, SignUp};
pub use contact::Contact;
pub use dashboard::Dashboard;
pub use home::Home;
pub use platform::Platform;
pub use pricing::Pricing;
pub use solutions::Solutions;
