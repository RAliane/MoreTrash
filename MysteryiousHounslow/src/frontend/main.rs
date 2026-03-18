// Main entry point for Matchgorithm Dioxus application
// This file initializes the web server, connects to backend services (Directus, Hasura, Postgres),
// and launches the Dioxus frontend with SSR support

use axum::{
    routing::{get, post},
    Router,
};
use dioxus::prelude::*;
use dioxus_fullstack::prelude::*;
use tower_http::{
    compression::CompressionLayer,
    cors::{Any, CorsLayer},
    services::ServeDir,
};
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

mod components;
mod pages;
mod services;
mod utils;

use config::AppConfig;

#[tokio::main]
async fn main() {
    // Initialize tracing for logging
    tracing_subscriber::registry()
        .with(tracing_subscriber::EnvFilter::new(
            std::env::var("RUST_LOG").unwrap_or_else(|_| "info".into()),
        ))
        .with(tracing_subscriber::fmt::layer())
        .init();

    // Load configuration from environment variables (injected via Podman secrets)
    let config = AppConfig::from_env().expect("Failed to load configuration");

    tracing::info!("Starting Matchgorithm server...");
    tracing::info!("Directus URL: {}", config.directus_url);
    tracing::info!("Hasura URL: {}", config.hasura_url);
    tracing::info!("Database URL configured: {}", !config.database_url.is_empty());

    // Initialize database connection pool
    let db_pool = services::database::init_pool(&config.database_url)
        .await
        .expect("Failed to connect to database");

    // Initialize Directus client
    let directus_client = services::directus::DirectusClient::new(
        config.directus_url.clone(),
        config.directus_api_key.clone(),
    );

    // Initialize Hasura client
    let hasura_client = services::hasura::HasuraClient::new(
        config.hasura_url.clone(),
        config.hasura_admin_secret.clone(),
    );

    // Initialize JWT service
    let jwt_service = services::auth::jwt::JwtService::new(
        &config.jwt_private_key_pem,
        &config.jwt_public_key_pem,
    ).expect("Failed to initialize JWT service");

    // Initialize Directus auth client
    let directus_auth_client = services::auth::directus::DirectusAuthClient::new(
        config.directus_url.clone(),
        config.directus_api_key.clone(),
    );

    // Create application state
    let app_state = services::AppState {
        config: config.clone(),
        db_pool,
        directus_client,
        hasura_client,
        jwt_service,
        directus_auth_client,
    };

    // Build Axum router with Dioxus integration
    let app = Router::new()
        // Serve static files (CSS, JS, images)
        .nest_service("/assets", ServeDir::new("assets"))
        .nest_service("/public", ServeDir::new("public"))
         // API routes
         .route("/api/health", get(health_check))
         .route("/api/auth/login", post(services::auth::login))
         .route("/api/auth/register", post(services::auth::register))
         .route("/api/auth/logout", post(services::auth::logout))
         .route("/api/graphql", post(services::hasura::graphql_proxy))
         .route("/api/cms/:endpoint", get(services::directus::cms_proxy))
        // Dioxus SSR route - handles all frontend pages
        .fallback(get(|req| async move {
            dioxus_web::launch::launch_server(req, App, ServeConfig::default()).await
        }))
        // Middleware
        .layer(CompressionLayer::new())
        .layer(middleware::cors::create_cors_layer())
        .layer(middleware::security::create_security_headers_layer())
        .with_state(app_state);

    // Start server
    let addr = format!("{}:{}", config.server_host, config.server_port);
    let listener = tokio::net::TcpListener::bind(&addr)
        .await
        .expect("Failed to bind to address");

    tracing::info!("Matchgorithm running at http://{}", addr);

    axum::serve(listener, app)
        .await
        .expect("Server error");
}

// Root Dioxus application component
// This component sets up routing and renders the appropriate page based on URL
#[component]
fn App() -> Element {
    rsx! {
        Router::<Route> {}
    }
}

// Define all application routes
#[derive(Clone, Routable, Debug, PartialEq)]
#[rustfmt::skip]
enum Route {
    #[route("/")]
    Home {},
    #[route("/platform")]
    Platform {},
    #[route("/solutions")]
    Solutions {},
    #[route("/about")]
    About {},
    #[route("/contact")]
    Contact {},
    #[route("/pricing")]
    Pricing {},
    #[route("/blog")]
    Blog {},
    #[route("/careers")]
    Careers {},
    #[route("/docs")]
    Docs {},
    #[route("/api-docs")]
    ApiDocs {},
    #[route("/chat")]
    Chat {},
    #[route("/login")]
    Login {},
    #[route("/auth/sign-up")]
    SignUp {},
    #[route("/forgot-password")]
    ForgotPassword {},
    #[route("/reset-password")]
    ResetPassword {},
    #[route("/dashboard")]
    Dashboard {},
    #[route("/matches")]
    Matches {},
    #[route("/dashboard/profile")]
    DashboardProfile {},
    #[route("/dashboard/analytics")]
    DashboardAnalytics {},
    #[route("/admin")]
    AdminDashboard {},
    #[route("/admin/users")]
    AdminUsers {},
    #[route("/admin/analytics")]
    AdminAnalytics {},
    #[route("/admin/settings")]
    AdminSettings {},
    #[route("/privacy")]
    Privacy {},
    #[route("/terms")]
    Terms {},
    #[route("/:..route")]
    NotFound { route: Vec<String> },
}

// Component implementations for routes

#[component]
fn Home() -> Element {
    pages::Home {}
}

#[component]
fn Platform() -> Element {
    rsx! {
        div {
            class: "min-h-screen bg-gray-50",
            div {
                class: "max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8",
                h1 {
                    class: "text-3xl font-bold text-gray-900",
                    "Platform"
                }
                p {
                    class: "mt-2 text-sm text-gray-600",
                    "Platform details and features coming soon."
                }
            }
        }
    }
}

#[component]
fn Solutions() -> Element {
    rsx! {
        div {
            class: "min-h-screen bg-gray-50",
            div {
                class: "max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8",
                h1 {
                    class: "text-3xl font-bold text-gray-900",
                    "Solutions"
                }
                p {
                    class: "mt-2 text-sm text-gray-600",
                    "Our solutions for various matching needs."
                }
            }
        }
    }
}

#[component]
fn About() -> Element {
    rsx! {
        div {
            class: "min-h-screen bg-gray-50",
            div {
                class: "max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8",
                h1 {
                    class: "text-3xl font-bold text-gray-900",
                    "About Matchgorithm"
                }
                p {
                    class: "mt-2 text-sm text-gray-600",
                    "Learn about our mission and team."
                }
            }
        }
    }
}

#[component]
fn Contact() -> Element {
    rsx! {
        div {
            class: "min-h-screen bg-gray-50",
            div {
                class: "max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8",
                h1 {
                    class: "text-3xl font-bold text-gray-900",
                    "Contact Us"
                }
                p {
                    class: "mt-2 text-sm text-gray-600",
                    "Get in touch with our team."
                }
            }
        }
    }
}

#[component]
fn Pricing() -> Element {
    rsx! {
        div {
            class: "min-h-screen bg-gray-50",
            div {
                class: "max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8",
                h1 {
                    class: "text-3xl font-bold text-gray-900",
                    "Pricing"
                }
                p {
                    class: "mt-2 text-sm text-gray-600",
                    "Choose the plan that fits your needs."
                }
            }
        }
    }
}

#[component]
fn Blog() -> Element {
    rsx! {
        div {
            class: "min-h-screen bg-gray-50",
            div {
                class: "max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8",
                h1 {
                    class: "text-3xl font-bold text-gray-900",
                    "Blog"
                }
                p {
                    class: "mt-2 text-sm text-gray-600",
                    "Latest news and insights."
                }
            }
        }
    }
}

#[component]
fn Careers() -> Element {
    rsx! {
        div {
            class: "min-h-screen bg-gray-50",
            div {
                class: "max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8",
                h1 {
                    class: "text-3xl font-bold text-gray-900",
                    "Careers"
                }
                p {
                    class: "mt-2 text-sm text-gray-600",
                    "Join our team."
                }
            }
        }
    }
}

#[component]
fn Docs() -> Element {
    rsx! {
        div {
            class: "min-h-screen bg-gray-50",
            div {
                class: "max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8",
                h1 {
                    class: "text-3xl font-bold text-gray-900",
                    "Documentation"
                }
                p {
                    class: "mt-2 text-sm text-gray-600",
                    "API and usage documentation."
                }
            }
        }
    }
}

#[component]
fn ApiDocs() -> Element {
    rsx! {
        div {
            class: "min-h-screen bg-gray-50",
            div {
                class: "max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8",
                h1 {
                    class: "text-3xl font-bold text-gray-900",
                    "API Documentation"
                }
                p {
                    class: "mt-2 text-sm text-gray-600",
                    "Detailed API reference."
                }
            }
        }
    }
}

#[component]
fn Chat() -> Element {
    rsx! {
        div {
            class: "min-h-screen bg-gray-50",
            div {
                class: "max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8",
                h1 {
                    class: "text-3xl font-bold text-gray-900",
                    "Chat Support"
                }
                p {
                    class: "mt-2 text-sm text-gray-600",
                    "Get help from our support team."
                }
            }
        }
    }
}

#[component]
fn Login() -> Element {
    pages::Login {}
}

#[component]
fn SignUp() -> Element {
    components::AuthLayout {
        rsx! {
            form {
                class: "space-y-4",
                div {
                    label {
                        class: "block text-sm font-medium text-gray-700",
                        r#for: "email",
                        "Email"
                    }
                    input {
                        id: "email",
                        name: "email",
                        r#type: "email",
                        required: true,
                        class: "mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500",
                        placeholder: "Enter your email"
                    }
                }
                div {
                    label {
                        class: "block text-sm font-medium text-gray-700",
                        r#for: "password",
                        "Password"
                    }
                    input {
                        id: "password",
                        name: "password",
                        r#type: "password",
                        required: true,
                        class: "mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500",
                        placeholder: "Create a password"
                    }
                }
                button {
                    r#type: "submit",
                    class: "w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500",
                    "Sign Up"
                }
            }
        }
    }
}

#[component]
fn ForgotPassword() -> Element {
    components::AuthLayout {
        rsx! {
            form {
                class: "space-y-4",
                div {
                    label {
                        class: "block text-sm font-medium text-gray-700",
                        r#for: "email",
                        "Email"
                    }
                    input {
                        id: "email",
                        name: "email",
                        r#type: "email",
                        required: true,
                        class: "mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500",
                        placeholder: "Enter your email"
                    }
                }
                button {
                    r#type: "submit",
                    class: "w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500",
                    "Reset Password"
                }
            }
        }
    }
}

#[component]
fn Dashboard() -> Element {
    pages::Dashboard {}
}

#[component]
fn Matches() -> Element {
    pages::Matches {}
}

#[component]
fn DashboardProfile() -> Element {
    rsx! {
        div {
            class: "min-h-screen bg-gray-50",
            div {
                class: "max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8",
                h1 {
                    class: "text-3xl font-bold text-gray-900",
                    "Profile Settings"
                }
                p {
                    class: "mt-2 text-sm text-gray-600",
                    "Manage your profile information."
                }
            }
        }
    }
}

#[component]
fn DashboardAnalytics() -> Element {
    rsx! {
        div {
            class: "min-h-screen bg-gray-50",
            div {
                class: "max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8",
                h1 {
                    class: "text-3xl font-bold text-gray-900",
                    "Analytics"
                }
                p {
                    class: "mt-2 text-sm text-gray-600",
                    "View your matching analytics."
                }
            }
        }
    }
}

#[component]
fn AdminDashboard() -> Element {
    pages::AdminDashboard {}
}

#[component]
fn AdminUsers() -> Element {
    rsx! {
        div {
            class: "min-h-screen bg-gray-50",
            div {
                class: "max-w-7xl mx-auto py-12 px-4 sm:px-8",
                h1 {
                    class: "text-3xl font-bold text-gray-900",
                    "User Management"
                }
                p {
                    class: "mt-2 text-sm text-gray-600",
                    "Manage user accounts and permissions."
                }
            }
        }
    }
}

#[component]
fn AdminAnalytics() -> Element {
    rsx! {
        div {
            class: "min-h-screen bg-gray-50",
            div {
                class: "max-w-7xl mx-auto py-12 px-4 sm:px-8",
                h1 {
                    class: "text-3xl font-bold text-gray-900",
                    "Admin Analytics"
                }
                p {
                    class: "mt-2 text-sm text-gray-600",
                    "System-wide analytics and metrics."
                }
            }
        }
    }
}

#[component]
fn AdminSettings() -> Element {
    rsx! {
        div {
            class: "min-h-screen bg-gray-50",
            div {
                class: "max-w-7xl mx-auto py-12 px-4 sm:px-8",
                h1 {
                    class: "text-3xl font-bold text-gray-900",
                    "System Settings"
                }
                p {
                    class: "mt-2 text-sm text-gray-600",
                    "Configure system-wide settings."
                }
            }
        }
    }
}

#[component]
fn Privacy() -> Element {
    rsx! {
        div {
            class: "min-h-screen bg-gray-50",
            div {
                class: "max-w-7xl mx-auto py-12 px-4 sm:px-8",
                h1 {
                    class: "text-3xl font-bold text-gray-900",
                    "Privacy Policy"
                }
                p {
                    class: "mt-2 text-sm text-gray-600",
                    "Our commitment to your privacy."
                }
            }
        }
    }
}

#[component]
fn Terms() -> Element {
    rsx! {
        div {
            class: "min-h-screen bg-gray-50",
            div {
                class: "max-w-7xl mx-auto py-12 px-4 sm:px-8",
                h1 {
                    class: "text-3xl font-bold text-gray-900",
                    "Terms of Service"
                }
                p {
                    class: "mt-2 text-sm text-gray-600",
                    "Terms and conditions for using our service."
                }
            }
        }
    }
}

#[component]
fn NotFound(route: Vec<String>) -> Element {
    rsx! {
        div {
            class: "min-h-screen bg-gray-50",
            div {
                class: "max-w-7xl mx-auto py-12 px-4 sm:px-8",
                h1 {
                    class: "text-3xl font-bold text-gray-900",
                    "404 - Page Not Found"
                }
                p {
                    class: "mt-2 text-sm text-gray-600",
                    "The page you're looking for doesn't exist."
                }
                p {
                    class: "mt-2 text-sm text-gray-500",
                    "Route: {route.join(\"/\")}"
                }
            }
        }
    }
}

// Health check endpoint for monitoring
async fn health_check() -> &'static str {
    "OK"
}
