//! Site header component with auth-aware navigation

use dioxus::prelude::*;

fn is_authenticated() -> bool {
    if let Some(window) = web_sys::window() {
        if let Ok(Some(storage)) = window.local_storage() {
            return storage.get_item("auth_token").ok().flatten().is_some();
        }
    }
    false
}

#[component]
pub fn Header() -> Element {
    let authenticated = use_signal(is_authenticated);

    rsx! {
        header { class: "border-b border-slate-800 bg-slate-950/95 backdrop-blur sticky top-0 z-50",
            div { class: "max-w-7xl mx-auto px-4 sm:px-6 lg:px-8",
                div { class: "flex items-center justify-between h-16",
                    // Logo
                    a { href: "/", class: "text-xl font-bold text-white",
                        "Matchgorithm"
                    }
                    // Navigation
                    nav { class: "hidden md:flex items-center gap-6",
                        a { href: "/platform", class: "text-slate-400 hover:text-white transition", "Platform" }
                        a { href: "/solutions", class: "text-slate-400 hover:text-white transition", "Solutions" }
                        a { href: "/pricing", class: "text-slate-400 hover:text-white transition", "Pricing" }
                        a { href: "/about", class: "text-slate-400 hover:text-white transition", "About" }
                        a { href: "/contact", class: "text-slate-400 hover:text-white transition", "Contact" }
                    }
                    // Auth buttons
                    div { class: "flex items-center gap-4",
                        if authenticated() {
                            a { href: "/dashboard", class: "text-slate-400 hover:text-white transition", "Dashboard" }
                        } else {
                            a { href: "/auth/sign-in", class: "text-slate-400 hover:text-white transition", "Sign In" }
                            a {
                                href: "/auth/sign-up",
                                class: "px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-500 transition font-medium",
                                "Get Started"
                            }
                        }
                    }
                }
            }
        }
    }
}
