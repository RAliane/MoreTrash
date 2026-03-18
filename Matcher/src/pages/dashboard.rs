//! Dashboard pages - user dashboard with profile, analytics, and settings

use dioxus::prelude::*;

/// User data stored in localStorage
#[derive(Clone, Debug, Default)]
struct UserState {
    is_authenticated: bool,
    first_name: String,
    last_name: String,
    email: String,
}

fn get_user_state() -> UserState {
    if let Some(window) = web_sys::window() {
        if let Ok(Some(storage)) = window.local_storage() {
            if storage.get_item("auth_token").ok().flatten().is_some() {
                return UserState {
                    is_authenticated: true,
                    first_name: storage
                        .get_item("user_first_name")
                        .ok()
                        .flatten()
                        .unwrap_or_default(),
                    last_name: storage
                        .get_item("user_last_name")
                        .ok()
                        .flatten()
                        .unwrap_or_default(),
                    email: storage
                        .get_item("user_email")
                        .ok()
                        .flatten()
                        .unwrap_or_default(),
                };
            }
        }
    }
    UserState::default()
}

fn logout() {
    if let Some(window) = web_sys::window() {
        if let Ok(Some(storage)) = window.local_storage() {
            let _ = storage.remove_item("auth_token");
            let _ = storage.remove_item("user_first_name");
            let _ = storage.remove_item("user_last_name");
            let _ = storage.remove_item("user_email");
        }
        let _ = window.location().set_href("/");
    }
}

#[component]
pub fn Dashboard() -> Element {
    let user = use_signal(get_user_state);
    let current_path = use_signal(|| "/dashboard".to_string());

    // Redirect if not authenticated
    if !user().is_authenticated {
        if let Some(window) = web_sys::window() {
            let _ = window.location().set_href("/auth/sign-in");
        }
        return rsx! { div { "Redirecting..." } };
    }

    rsx! {
        div { class: "min-h-screen bg-slate-950 flex",
            // Sidebar
            aside { class: "w-64 bg-slate-900 border-r border-slate-800 flex flex-col",
                // Logo
                div { class: "p-6 border-b border-slate-800",
                    a { href: "/", class: "text-xl font-bold text-white",
                        "Matchgorithm"
                    }
                }

                // Navigation
                nav { class: "flex-1 p-4 space-y-1",
                    SidebarLink { href: "/dashboard", label: "Overview", icon: "home", active: current_path() == "/dashboard" }
                    SidebarLink { href: "/dashboard/matches", label: "Matches", icon: "users", active: current_path() == "/dashboard/matches" }
                    SidebarLink { href: "/dashboard/profile", label: "Profile", icon: "user", active: current_path() == "/dashboard/profile" }
                    SidebarLink { href: "/dashboard/analytics", label: "Analytics", icon: "chart", active: current_path() == "/dashboard/analytics" }
                    SidebarLink { href: "/dashboard/settings", label: "Settings", icon: "settings", active: current_path() == "/dashboard/settings" }
                }

                // User section
                div { class: "p-4 border-t border-slate-800",
                    div { class: "flex items-center gap-3 mb-3",
                        div { class: "w-10 h-10 bg-blue-600 rounded-full flex items-center justify-center text-white font-semibold",
                            "{user().first_name.chars().next().unwrap_or('U')}"
                        }
                        div { class: "flex-1 min-w-0",
                            p { class: "text-sm font-medium text-white truncate",
                                "{user().first_name} {user().last_name}"
                            }
                            p { class: "text-xs text-slate-400 truncate",
                                "{user().email}"
                            }
                        }
                    }
                    button {
                        onclick: move |_| logout(),
                        class: "w-full px-3 py-2 text-sm text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition text-left",
                        "Sign out"
                    }
                }
            }

            // Main content
            main { class: "flex-1 overflow-auto",
                // Header
                header { class: "bg-slate-900/50 border-b border-slate-800 px-8 py-4",
                    h1 { class: "text-2xl font-bold text-white",
                        "Welcome back, {user().first_name}"
                    }
                    p { class: "text-slate-400",
                        "Here's what's happening with your matches today."
                    }
                }

                // Dashboard content
                div { class: "p-8",
                    // Stats grid
                    div { class: "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8",
                        StatCard { label: "Total Matches", value: "248", change: "+12%", positive: true }
                        StatCard { label: "Active Connections", value: "56", change: "+8%", positive: true }
                        StatCard { label: "Match Score", value: "94%", change: "+2%", positive: true }
                        StatCard { label: "Response Rate", value: "87%", change: "-3%", positive: false }
                    }

                    // Recent activity
                    div { class: "grid lg:grid-cols-2 gap-8",
                        // Recent matches
                        div { class: "bg-slate-900 border border-slate-800 rounded-xl p-6",
                            h2 { class: "text-lg font-semibold text-white mb-4",
                                "Recent Matches"
                            }
                            div { class: "space-y-4",
                                MatchItem { name: "Sarah Chen", role: "Senior Developer", score: 96 }
                                MatchItem { name: "Marcus Johnson", role: "Product Manager", score: 92 }
                                MatchItem { name: "Elena Rodriguez", role: "UX Designer", score: 89 }
                                MatchItem { name: "James Wilson", role: "Data Scientist", score: 87 }
                            }
                            a { href: "/dashboard/matches", class: "block mt-4 text-blue-400 hover:text-blue-300 text-sm",
                                "View all matches →"
                            }
                        }

                        // Activity feed
                        div { class: "bg-slate-900 border border-slate-800 rounded-xl p-6",
                            h2 { class: "text-lg font-semibold text-white mb-4",
                                "Recent Activity"
                            }
                            div { class: "space-y-4",
                                ActivityItem { text: "New match found with 96% compatibility", time: "2 hours ago" }
                                ActivityItem { text: "Profile optimization completed", time: "5 hours ago" }
                                ActivityItem { text: "Connection request accepted", time: "1 day ago" }
                                ActivityItem { text: "Skills assessment updated", time: "2 days ago" }
                            }
                        }
                    }
                }
            }
        }
    }
}

#[component]
fn SidebarLink(
    href: &'static str,
    label: &'static str,
    icon: &'static str,
    active: bool,
) -> Element {
    let base_class = if active {
        "flex items-center gap-3 px-3 py-2 rounded-lg bg-blue-600 text-white"
    } else {
        "flex items-center gap-3 px-3 py-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
    };

    rsx! {
        a { href: href, class: base_class,
            span { class: "w-5 h-5",
                match icon {
                    "home" => rsx! { "🏠" },
                    "users" => rsx! { "👥" },
                    "user" => rsx! { "👤" },
                    "chart" => rsx! { "📊" },
                    "settings" => rsx! { "⚙️" },
                    _ => rsx! { "•" }
                }
            }
            "{label}"
        }
    }
}

#[component]
fn StatCard(
    label: &'static str,
    value: &'static str,
    change: &'static str,
    positive: bool,
) -> Element {
    let change_class = if positive {
        "text-green-400"
    } else {
        "text-red-400"
    };

    rsx! {
        div { class: "bg-slate-900 border border-slate-800 rounded-xl p-6",
            p { class: "text-slate-400 text-sm mb-1", "{label}" }
            p { class: "text-3xl font-bold text-white mb-1", "{value}" }
            p { class: "{change_class} text-sm", "{change} from last month" }
        }
    }
}

#[component]
fn MatchItem(name: &'static str, role: &'static str, score: u8) -> Element {
    rsx! {
        div { class: "flex items-center justify-between",
            div { class: "flex items-center gap-3",
                div { class: "w-10 h-10 bg-slate-700 rounded-full flex items-center justify-center text-white",
                    "{name.chars().next().unwrap_or('?')}"
                }
                div {
                    p { class: "text-white font-medium", "{name}" }
                    p { class: "text-slate-400 text-sm", "{role}" }
                }
            }
            div { class: "text-right",
                p { class: "text-green-400 font-semibold", "{score}%" }
                p { class: "text-slate-500 text-xs", "match" }
            }
        }
    }
}

#[component]
fn ActivityItem(text: &'static str, time: &'static str) -> Element {
    rsx! {
        div { class: "flex items-start gap-3",
            div { class: "w-2 h-2 mt-2 bg-blue-500 rounded-full" }
            div {
                p { class: "text-slate-300", "{text}" }
                p { class: "text-slate-500 text-sm", "{time}" }
            }
        }
    }
}

#[component]
pub fn DashboardProfile() -> Element {
    let mut first_name = use_signal(String::new);
    let mut last_name = use_signal(String::new);
    let mut email = use_signal(String::new);
    let mut bio = use_signal(String::new);
    let mut loading = use_signal(|| false);
    let mut success = use_signal(|| false);

    // Load user data on mount
    use_effect(move || {
        if let Some(window) = web_sys::window() {
            if let Ok(Some(storage)) = window.local_storage() {
                first_name.set(
                    storage
                        .get_item("user_first_name")
                        .ok()
                        .flatten()
                        .unwrap_or_default(),
                );
                last_name.set(
                    storage
                        .get_item("user_last_name")
                        .ok()
                        .flatten()
                        .unwrap_or_default(),
                );
                email.set(
                    storage
                        .get_item("user_email")
                        .ok()
                        .flatten()
                        .unwrap_or_default(),
                );
            }
        }
    });

    let handle_submit = move |evt: Event<FormData>| {
        evt.prevent_default();
        loading.set(true);
        success.set(false);

        spawn(async move {
            // Update profile via API
            let response = gloo_net::http::Request::patch("/api/cms/users/me")
                .header("Content-Type", "application/json")
                .body(
                    serde_json::json!({
                        "first_name": first_name(),
                        "last_name": last_name(),
                        "bio": bio()
                    })
                    .to_string(),
                )
                .unwrap()
                .send()
                .await;

            loading.set(false);

            if response.is_ok() {
                // Update localStorage
                if let Some(window) = web_sys::window() {
                    if let Ok(Some(storage)) = window.local_storage() {
                        let _ = storage.set_item("user_first_name", &first_name());
                        let _ = storage.set_item("user_last_name", &last_name());
                    }
                }
                success.set(true);
            }
        });
    };

    rsx! {
        div { class: "min-h-screen bg-slate-950 p-8",
            div { class: "max-w-2xl mx-auto",
                h1 { class: "text-3xl font-bold text-white mb-8", "Profile Settings" }

                if success() {
                    div { class: "bg-green-500/10 border border-green-500/50 text-green-400 px-4 py-3 rounded-lg mb-6",
                        "Profile updated successfully!"
                    }
                }

                form { onsubmit: handle_submit,
                    div { class: "bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6",
                        // Name fields
                        div { class: "grid grid-cols-2 gap-4",
                            div {
                                label { class: "block text-sm font-medium text-slate-300 mb-2", "First name" }
                                input {
                                    r#type: "text",
                                    class: "w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500",
                                    value: "{first_name}",
                                    oninput: move |evt| first_name.set(evt.value())
                                }
                            }
                            div {
                                label { class: "block text-sm font-medium text-slate-300 mb-2", "Last name" }
                                input {
                                    r#type: "text",
                                    class: "w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500",
                                    value: "{last_name}",
                                    oninput: move |evt| last_name.set(evt.value())
                                }
                            }
                        }

                        // Email (read-only)
                        div {
                            label { class: "block text-sm font-medium text-slate-300 mb-2", "Email" }
                            input {
                                r#type: "email",
                                class: "w-full px-4 py-3 bg-slate-800/50 border border-slate-700 rounded-lg text-slate-400 cursor-not-allowed",
                                value: "{email}",
                                disabled: true
                            }
                            p { class: "text-slate-500 text-sm mt-1", "Email cannot be changed" }
                        }

                        // Bio
                        div {
                            label { class: "block text-sm font-medium text-slate-300 mb-2", "Bio" }
                            textarea {
                                rows: 4,
                                class: "w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none",
                                placeholder: "Tell us about yourself...",
                                value: "{bio}",
                                oninput: move |evt| bio.set(evt.value())
                            }
                        }

                        // Submit
                        div { class: "flex justify-end",
                            button {
                                r#type: "submit",
                                disabled: loading(),
                                class: "px-6 py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-600/50 text-white font-semibold rounded-lg transition",
                                if loading() { "Saving..." } else { "Save Changes" }
                            }
                        }
                    }
                }
            }
        }
    }
}

#[component]
pub fn DashboardAnalytics() -> Element {
    rsx! {
        div { class: "min-h-screen bg-slate-950 p-8",
            h1 { class: "text-3xl font-bold text-white mb-8", "Analytics" }

            // Time period selector
            div { class: "flex gap-2 mb-8",
                button { class: "px-4 py-2 bg-blue-600 text-white rounded-lg", "7 days" }
                button { class: "px-4 py-2 bg-slate-800 text-slate-400 hover:text-white rounded-lg", "30 days" }
                button { class: "px-4 py-2 bg-slate-800 text-slate-400 hover:text-white rounded-lg", "90 days" }
            }

            // Charts placeholder
            div { class: "grid lg:grid-cols-2 gap-8",
                div { class: "bg-slate-900 border border-slate-800 rounded-xl p-6",
                    h2 { class: "text-lg font-semibold text-white mb-4", "Match Quality Over Time" }
                    div { class: "h-64 flex items-center justify-center text-slate-500",
                        "Chart visualization - connect to analytics API"
                    }
                }
                div { class: "bg-slate-900 border border-slate-800 rounded-xl p-6",
                    h2 { class: "text-lg font-semibold text-white mb-4", "Connection Rate" }
                    div { class: "h-64 flex items-center justify-center text-slate-500",
                        "Chart visualization - connect to analytics API"
                    }
                }
            }

            // Detailed stats
            div { class: "mt-8 bg-slate-900 border border-slate-800 rounded-xl p-6",
                h2 { class: "text-lg font-semibold text-white mb-4", "Performance Metrics" }
                div { class: "overflow-x-auto",
                    table { class: "w-full",
                        thead {
                            tr { class: "border-b border-slate-700",
                                th { class: "text-left py-3 px-4 text-slate-400 font-medium", "Metric" }
                                th { class: "text-left py-3 px-4 text-slate-400 font-medium", "This Period" }
                                th { class: "text-left py-3 px-4 text-slate-400 font-medium", "Previous" }
                                th { class: "text-left py-3 px-4 text-slate-400 font-medium", "Change" }
                            }
                        }
                        tbody {
                            tr { class: "border-b border-slate-800",
                                td { class: "py-3 px-4 text-white", "Profile Views" }
                                td { class: "py-3 px-4 text-white", "1,234" }
                                td { class: "py-3 px-4 text-slate-400", "1,089" }
                                td { class: "py-3 px-4 text-green-400", "+13.3%" }
                            }
                            tr { class: "border-b border-slate-800",
                                td { class: "py-3 px-4 text-white", "Matches Generated" }
                                td { class: "py-3 px-4 text-white", "248" }
                                td { class: "py-3 px-4 text-slate-400", "221" }
                                td { class: "py-3 px-4 text-green-400", "+12.2%" }
                            }
                            tr { class: "border-b border-slate-800",
                                td { class: "py-3 px-4 text-white", "Avg Match Score" }
                                td { class: "py-3 px-4 text-white", "94%" }
                                td { class: "py-3 px-4 text-slate-400", "92%" }
                                td { class: "py-3 px-4 text-green-400", "+2.2%" }
                            }
                            tr {
                                td { class: "py-3 px-4 text-white", "Response Rate" }
                                td { class: "py-3 px-4 text-white", "87%" }
                                td { class: "py-3 px-4 text-slate-400", "90%" }
                                td { class: "py-3 px-4 text-red-400", "-3.3%" }
                            }
                        }
                    }
                }
            }
        }
    }
}
