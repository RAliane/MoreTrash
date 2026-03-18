//! Authentication pages - sign in, sign up, forgot password, reset password
//!
//! All forms are wired to the Directus auth API via /api/auth/* endpoints.

use dioxus::prelude::*;

#[component]
pub fn SignIn() -> Element {
    let mut email = use_signal(String::new);
    let mut password = use_signal(String::new);
    let mut error = use_signal(|| None::<String>);
    let mut loading = use_signal(|| false);

    let handle_submit = move |evt: Event<FormData>| {
        evt.prevent_default();
        loading.set(true);
        error.set(None);

        spawn(async move {
            let response = gloo_net::http::Request::post("/api/auth/login")
                .header("Content-Type", "application/json")
                .body(
                    serde_json::json!({
                        "email": email(),
                        "password": password()
                    })
                    .to_string(),
                )
                .unwrap()
                .send()
                .await;

            loading.set(false);

            match response {
                Ok(res) if res.ok() => {
                    // Store token and redirect
                    if let Ok(data) = res.json::<serde_json::Value>().await {
                        if let Some(token) = data.get("access_token").and_then(|t| t.as_str()) {
                            // Store in localStorage
                            if let Some(window) = web_sys::window() {
                                if let Ok(Some(storage)) = window.local_storage() {
                                    let _ = storage.set_item("auth_token", token);
                                }
                            }
                            // Redirect to dashboard
                            let navigator = use_navigator();
                            navigator.push("/dashboard");
                        }
                    }
                }
                Ok(res) => {
                    error.set(Some("Invalid email or password".to_string()));
                }
                Err(e) => {
                    error.set(Some(format!("Network error: {}", e)));
                }
            }
        });
    };

    rsx! {
        main { class: "min-h-screen bg-slate-950 flex items-center justify-center px-4",
            div { class: "w-full max-w-md",
                // Logo
                a { href: "/", class: "flex items-center justify-center mb-8",
                    span { class: "text-2xl font-bold text-white", "Matchgorithm" }
                }

                // Card
                div { class: "bg-slate-900 border border-slate-800 rounded-xl p-8",
                    h1 { class: "text-2xl font-bold text-white mb-2 text-center",
                        "Welcome back"
                    }
                    p { class: "text-slate-400 text-center mb-8",
                        "Sign in to your account"
                    }

                    // OAuth Buttons
                    div { class: "space-y-3 mb-6",
                        OAuthButton { provider: "google", label: "Continue with Google" }
                        OAuthButton { provider: "github", label: "Continue with GitHub" }
                        OAuthButton { provider: "apple", label: "Continue with Apple" }
                    }

                    // Divider
                    div { class: "relative my-6",
                        div { class: "absolute inset-0 flex items-center",
                            div { class: "w-full border-t border-slate-700" }
                        }
                        div { class: "relative flex justify-center text-sm",
                            span { class: "px-2 bg-slate-900 text-slate-400", "Or continue with email" }
                        }
                    }

                    // Error message
                    if let Some(err) = error() {
                        div { class: "bg-red-500/10 border border-red-500/50 text-red-400 px-4 py-3 rounded-lg mb-4",
                            "{err}"
                        }
                    }

                    // Form
                    form { onsubmit: handle_submit,
                        div { class: "space-y-4",
                            // Email
                            div {
                                label { r#for: "email", class: "block text-sm font-medium text-slate-300 mb-2",
                                    "Email"
                                }
                                input {
                                    r#type: "email",
                                    id: "email",
                                    name: "email",
                                    required: true,
                                    class: "w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                                    placeholder: "name@example.com",
                                    value: "{email}",
                                    oninput: move |evt| email.set(evt.value())
                                }
                            }

                            // Password
                            div {
                                div { class: "flex justify-between items-center mb-2",
                                    label { r#for: "password", class: "block text-sm font-medium text-slate-300",
                                        "Password"
                                    }
                                    a { href: "/auth/forgot-password", class: "text-sm text-blue-400 hover:text-blue-300",
                                        "Forgot password?"
                                    }
                                }
                                input {
                                    r#type: "password",
                                    id: "password",
                                    name: "password",
                                    required: true,
                                    class: "w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                                    placeholder: "Enter your password",
                                    value: "{password}",
                                    oninput: move |evt| password.set(evt.value())
                                }
                            }

                            // Submit
                            button {
                                r#type: "submit",
                                disabled: loading(),
                                class: "w-full px-4 py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-600/50 text-white font-semibold rounded-lg transition",
                                if loading() { "Signing in..." } else { "Sign In" }
                            }
                        }
                    }

                    // Sign up link
                    p { class: "mt-6 text-center text-slate-400",
                        "Don't have an account? "
                        a { href: "/auth/sign-up", class: "text-blue-400 hover:text-blue-300 font-medium",
                            "Sign up"
                        }
                    }
                }
            }
        }
    }
}

#[component]
pub fn SignUp() -> Element {
    let mut first_name = use_signal(String::new);
    let mut last_name = use_signal(String::new);
    let mut email = use_signal(String::new);
    let mut password = use_signal(String::new);
    let mut confirm_password = use_signal(String::new);
    let mut error = use_signal(|| None::<String>);
    let mut loading = use_signal(|| false);

    let handle_submit = move |evt: Event<FormData>| {
        evt.prevent_default();

        // Validation
        if password() != confirm_password() {
            error.set(Some("Passwords do not match".to_string()));
            return;
        }

        if password().len() < 8 {
            error.set(Some("Password must be at least 8 characters".to_string()));
            return;
        }

        loading.set(true);
        error.set(None);

        spawn(async move {
            let response = gloo_net::http::Request::post("/api/auth/register")
                .header("Content-Type", "application/json")
                .body(
                    serde_json::json!({
                        "email": email(),
                        "password": password(),
                        "first_name": first_name(),
                        "last_name": last_name()
                    })
                    .to_string(),
                )
                .unwrap()
                .send()
                .await;

            loading.set(false);

            match response {
                Ok(res) if res.ok() => {
                    // Redirect to sign in
                    let navigator = use_navigator();
                    navigator.push("/auth/sign-in?registered=true");
                }
                Ok(res) => {
                    if let Ok(data) = res.json::<serde_json::Value>().await {
                        let msg = data
                            .get("message")
                            .and_then(|m| m.as_str())
                            .unwrap_or("Registration failed");
                        error.set(Some(msg.to_string()));
                    } else {
                        error.set(Some("Registration failed".to_string()));
                    }
                }
                Err(e) => {
                    error.set(Some(format!("Network error: {}", e)));
                }
            }
        });
    };

    rsx! {
        main { class: "min-h-screen bg-slate-950 flex items-center justify-center px-4 py-12",
            div { class: "w-full max-w-md",
                // Logo
                a { href: "/", class: "flex items-center justify-center mb-8",
                    span { class: "text-2xl font-bold text-white", "Matchgorithm" }
                }

                // Card
                div { class: "bg-slate-900 border border-slate-800 rounded-xl p-8",
                    h1 { class: "text-2xl font-bold text-white mb-2 text-center",
                        "Create an account"
                    }
                    p { class: "text-slate-400 text-center mb-8",
                        "Get started with Matchgorithm"
                    }

                    // OAuth Buttons
                    div { class: "space-y-3 mb-6",
                        OAuthButton { provider: "google", label: "Sign up with Google" }
                        OAuthButton { provider: "github", label: "Sign up with GitHub" }
                        OAuthButton { provider: "apple", label: "Sign up with Apple" }
                    }

                    // Divider
                    div { class: "relative my-6",
                        div { class: "absolute inset-0 flex items-center",
                            div { class: "w-full border-t border-slate-700" }
                        }
                        div { class: "relative flex justify-center text-sm",
                            span { class: "px-2 bg-slate-900 text-slate-400", "Or continue with email" }
                        }
                    }

                    // Error message
                    if let Some(err) = error() {
                        div { class: "bg-red-500/10 border border-red-500/50 text-red-400 px-4 py-3 rounded-lg mb-4",
                            "{err}"
                        }
                    }

                    // Form
                    form { onsubmit: handle_submit,
                        div { class: "space-y-4",
                            // Name row
                            div { class: "grid grid-cols-2 gap-4",
                                div {
                                    label { r#for: "first_name", class: "block text-sm font-medium text-slate-300 mb-2",
                                        "First name"
                                    }
                                    input {
                                        r#type: "text",
                                        id: "first_name",
                                        name: "first_name",
                                        required: true,
                                        class: "w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                                        placeholder: "John",
                                        value: "{first_name}",
                                        oninput: move |evt| first_name.set(evt.value())
                                    }
                                }
                                div {
                                    label { r#for: "last_name", class: "block text-sm font-medium text-slate-300 mb-2",
                                        "Last name"
                                    }
                                    input {
                                        r#type: "text",
                                        id: "last_name",
                                        name: "last_name",
                                        required: true,
                                        class: "w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                                        placeholder: "Doe",
                                        value: "{last_name}",
                                        oninput: move |evt| last_name.set(evt.value())
                                    }
                                }
                            }

                            // Email
                            div {
                                label { r#for: "email", class: "block text-sm font-medium text-slate-300 mb-2",
                                    "Email"
                                }
                                input {
                                    r#type: "email",
                                    id: "email",
                                    name: "email",
                                    required: true,
                                    class: "w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                                    placeholder: "name@example.com",
                                    value: "{email}",
                                    oninput: move |evt| email.set(evt.value())
                                }
                            }

                            // Password
                            div {
                                label { r#for: "password", class: "block text-sm font-medium text-slate-300 mb-2",
                                    "Password"
                                }
                                input {
                                    r#type: "password",
                                    id: "password",
                                    name: "password",
                                    required: true,
                                    minlength: 8,
                                    class: "w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                                    placeholder: "At least 8 characters",
                                    value: "{password}",
                                    oninput: move |evt| password.set(evt.value())
                                }
                            }

                            // Confirm Password
                            div {
                                label { r#for: "confirm_password", class: "block text-sm font-medium text-slate-300 mb-2",
                                    "Confirm password"
                                }
                                input {
                                    r#type: "password",
                                    id: "confirm_password",
                                    name: "confirm_password",
                                    required: true,
                                    class: "w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                                    placeholder: "Confirm your password",
                                    value: "{confirm_password}",
                                    oninput: move |evt| confirm_password.set(evt.value())
                                }
                            }

                            // Terms
                            p { class: "text-sm text-slate-400",
                                "By signing up, you agree to our "
                                a { href: "/terms", class: "text-blue-400 hover:text-blue-300", "Terms of Service" }
                                " and "
                                a { href: "/privacy", class: "text-blue-400 hover:text-blue-300", "Privacy Policy" }
                                "."
                            }

                            // Submit
                            button {
                                r#type: "submit",
                                disabled: loading(),
                                class: "w-full px-4 py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-600/50 text-white font-semibold rounded-lg transition",
                                if loading() { "Creating account..." } else { "Create Account" }
                            }
                        }
                    }

                    // Sign in link
                    p { class: "mt-6 text-center text-slate-400",
                        "Already have an account? "
                        a { href: "/auth/sign-in", class: "text-blue-400 hover:text-blue-300 font-medium",
                            "Sign in"
                        }
                    }
                }
            }
        }
    }
}

#[component]
pub fn ForgotPassword() -> Element {
    let mut email = use_signal(String::new);
    let mut error = use_signal(|| None::<String>);
    let mut success = use_signal(|| false);
    let mut loading = use_signal(|| false);

    let handle_submit = move |evt: Event<FormData>| {
        evt.prevent_default();
        loading.set(true);
        error.set(None);

        spawn(async move {
            let response = gloo_net::http::Request::post("/api/auth/forgot-password")
                .header("Content-Type", "application/json")
                .body(
                    serde_json::json!({
                        "email": email()
                    })
                    .to_string(),
                )
                .unwrap()
                .send()
                .await;

            loading.set(false);

            match response {
                Ok(res) if res.ok() => {
                    success.set(true);
                }
                Ok(_) | Err(_) => {
                    // Always show success to prevent email enumeration
                    success.set(true);
                }
            }
        });
    };

    rsx! {
        main { class: "min-h-screen bg-slate-950 flex items-center justify-center px-4",
            div { class: "w-full max-w-md",
                // Logo
                a { href: "/", class: "flex items-center justify-center mb-8",
                    span { class: "text-2xl font-bold text-white", "Matchgorithm" }
                }

                // Card
                div { class: "bg-slate-900 border border-slate-800 rounded-xl p-8",
                    if success() {
                        // Success state
                        div { class: "text-center",
                            div { class: "w-16 h-16 bg-green-500/10 rounded-full flex items-center justify-center mx-auto mb-4",
                                svg { class: "w-8 h-8 text-green-500",
                                    xmlns: "http://www.w3.org/2000/svg",
                                    fill: "none",
                                    view_box: "0 0 24 24",
                                    stroke: "currentColor",
                                    stroke_width: "2",
                                    path {
                                        stroke_linecap: "round",
                                        stroke_linejoin: "round",
                                        d: "M5 13l4 4L19 7"
                                    }
                                }
                            }
                            h1 { class: "text-2xl font-bold text-white mb-2",
                                "Check your email"
                            }
                            p { class: "text-slate-400 mb-6",
                                "If an account exists for {email}, you will receive a password reset link shortly."
                            }
                            a { href: "/auth/sign-in", class: "text-blue-400 hover:text-blue-300 font-medium",
                                "Back to sign in"
                            }
                        }
                    } else {
                        // Form state
                        h1 { class: "text-2xl font-bold text-white mb-2 text-center",
                            "Forgot your password?"
                        }
                        p { class: "text-slate-400 text-center mb-8",
                            "Enter your email and we'll send you a reset link"
                        }

                        // Error message
                        if let Some(err) = error() {
                            div { class: "bg-red-500/10 border border-red-500/50 text-red-400 px-4 py-3 rounded-lg mb-4",
                                "{err}"
                            }
                        }

                        // Form
                        form { onsubmit: handle_submit,
                            div { class: "space-y-4",
                                div {
                                    label { r#for: "email", class: "block text-sm font-medium text-slate-300 mb-2",
                                        "Email"
                                    }
                                    input {
                                        r#type: "email",
                                        id: "email",
                                        name: "email",
                                        required: true,
                                        class: "w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                                        placeholder: "name@example.com",
                                        value: "{email}",
                                        oninput: move |evt| email.set(evt.value())
                                    }
                                }

                                button {
                                    r#type: "submit",
                                    disabled: loading(),
                                    class: "w-full px-4 py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-600/50 text-white font-semibold rounded-lg transition",
                                    if loading() { "Sending..." } else { "Send Reset Link" }
                                }
                            }
                        }

                        p { class: "mt-6 text-center text-slate-400",
                            a { href: "/auth/sign-in", class: "text-blue-400 hover:text-blue-300 font-medium",
                                "Back to sign in"
                            }
                        }
                    }
                }
            }
        }
    }
}

#[component]
pub fn ResetPassword() -> Element {
    let mut password = use_signal(String::new);
    let mut confirm_password = use_signal(String::new);
    let mut error = use_signal(|| None::<String>);
    let mut success = use_signal(|| false);
    let mut loading = use_signal(|| false);

    // Get token from URL query params
    let token = use_memo(|| {
        if let Some(window) = web_sys::window() {
            if let Ok(search) = window.location().search() {
                let params = web_sys::UrlSearchParams::new_with_str(&search).ok()?;
                return params.get("token");
            }
        }
        None
    });

    let handle_submit = move |evt: Event<FormData>| {
        evt.prevent_default();

        if password() != confirm_password() {
            error.set(Some("Passwords do not match".to_string()));
            return;
        }

        if password().len() < 8 {
            error.set(Some("Password must be at least 8 characters".to_string()));
            return;
        }

        let Some(t) = token() else {
            error.set(Some("Invalid or missing reset token".to_string()));
            return;
        };

        loading.set(true);
        error.set(None);

        spawn(async move {
            let response = gloo_net::http::Request::post("/api/auth/reset-password")
                .header("Content-Type", "application/json")
                .body(
                    serde_json::json!({
                        "token": t,
                        "password": password()
                    })
                    .to_string(),
                )
                .unwrap()
                .send()
                .await;

            loading.set(false);

            match response {
                Ok(res) if res.ok() => {
                    success.set(true);
                }
                Ok(res) => {
                    if let Ok(data) = res.json::<serde_json::Value>().await {
                        let msg = data
                            .get("message")
                            .and_then(|m| m.as_str())
                            .unwrap_or("Failed to reset password");
                        error.set(Some(msg.to_string()));
                    } else {
                        error.set(Some("Failed to reset password".to_string()));
                    }
                }
                Err(e) => {
                    error.set(Some(format!("Network error: {}", e)));
                }
            }
        });
    };

    rsx! {
        main { class: "min-h-screen bg-slate-950 flex items-center justify-center px-4",
            div { class: "w-full max-w-md",
                // Logo
                a { href: "/", class: "flex items-center justify-center mb-8",
                    span { class: "text-2xl font-bold text-white", "Matchgorithm" }
                }

                // Card
                div { class: "bg-slate-900 border border-slate-800 rounded-xl p-8",
                    if success() {
                        // Success state
                        div { class: "text-center",
                            div { class: "w-16 h-16 bg-green-500/10 rounded-full flex items-center justify-center mx-auto mb-4",
                                svg { class: "w-8 h-8 text-green-500",
                                    xmlns: "http://www.w3.org/2000/svg",
                                    fill: "none",
                                    view_box: "0 0 24 24",
                                    stroke: "currentColor",
                                    stroke_width: "2",
                                    path {
                                        stroke_linecap: "round",
                                        stroke_linejoin: "round",
                                        d: "M5 13l4 4L19 7"
                                    }
                                }
                            }
                            h1 { class: "text-2xl font-bold text-white mb-2",
                                "Password reset successful"
                            }
                            p { class: "text-slate-400 mb-6",
                                "Your password has been updated. You can now sign in with your new password."
                            }
                            a {
                                href: "/auth/sign-in",
                                class: "inline-block px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-lg transition",
                                "Sign in"
                            }
                        }
                    } else {
                        // Form state
                        h1 { class: "text-2xl font-bold text-white mb-2 text-center",
                            "Reset your password"
                        }
                        p { class: "text-slate-400 text-center mb-8",
                            "Enter your new password below"
                        }

                        // Error message
                        if let Some(err) = error() {
                            div { class: "bg-red-500/10 border border-red-500/50 text-red-400 px-4 py-3 rounded-lg mb-4",
                                "{err}"
                            }
                        }

                        // Form
                        form { onsubmit: handle_submit,
                            div { class: "space-y-4",
                                div {
                                    label { r#for: "password", class: "block text-sm font-medium text-slate-300 mb-2",
                                        "New password"
                                    }
                                    input {
                                        r#type: "password",
                                        id: "password",
                                        name: "password",
                                        required: true,
                                        minlength: 8,
                                        class: "w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                                        placeholder: "At least 8 characters",
                                        value: "{password}",
                                        oninput: move |evt| password.set(evt.value())
                                    }
                                }

                                div {
                                    label { r#for: "confirm_password", class: "block text-sm font-medium text-slate-300 mb-2",
                                        "Confirm new password"
                                    }
                                    input {
                                        r#type: "password",
                                        id: "confirm_password",
                                        name: "confirm_password",
                                        required: true,
                                        class: "w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                                        placeholder: "Confirm your password",
                                        value: "{confirm_password}",
                                        oninput: move |evt| confirm_password.set(evt.value())
                                    }
                                }

                                button {
                                    r#type: "submit",
                                    disabled: loading(),
                                    class: "w-full px-4 py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-600/50 text-white font-semibold rounded-lg transition",
                                    if loading() { "Resetting..." } else { "Reset Password" }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

#[component]
fn OAuthButton(provider: &'static str, label: &'static str) -> Element {
    let icon = match provider {
        "google" => rsx! {
            svg { class: "w-5 h-5",
                view_box: "0 0 24 24",
                path {
                    fill: "currentColor",
                    d: "M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                }
                path {
                    fill: "currentColor",
                    d: "M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                }
                path {
                    fill: "currentColor",
                    d: "M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                }
                path {
                    fill: "currentColor",
                    d: "M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                }
            }
        },
        "github" => rsx! {
            svg { class: "w-5 h-5",
                view_box: "0 0 24 24",
                fill: "currentColor",
                path {
                    d: "M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"
                }
            }
        },
        "apple" => rsx! {
            svg { class: "w-5 h-5",
                view_box: "0 0 24 24",
                fill: "currentColor",
                path {
                    d: "M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.81-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z"
                }
            }
        },
        _ => rsx! {},
    };

    let onclick = move |_| {
        // Redirect to OAuth provider
        if let Some(window) = web_sys::window() {
            let _ = window
                .location()
                .set_href(&format!("/api/auth/oauth/{}", provider));
        }
    };

    rsx! {
        button {
            r#type: "button",
            onclick: onclick,
            class: "w-full flex items-center justify-center gap-3 px-4 py-3 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-white font-medium transition",
            {icon}
            "{label}"
        }
    }
}
