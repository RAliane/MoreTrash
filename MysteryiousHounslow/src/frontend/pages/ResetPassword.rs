use dioxus::prelude::*;
use dioxus_router::use_route;

#[component]
pub fn ResetPassword() -> Element {
    let route = use_route();
    let mut password = use_signal(|| String::new());
    let mut confirm_password = use_signal(|| String::new());
    let mut message = use_signal(|| String::new());
    let mut is_loading = use_signal(|| false);

    // Extract token from URL query parameters
    let token = route.query_param("token").unwrap_or_default();

    let handle_submit = move |event: FormEvent| async move {
        event.prevent_default();

        if token.is_empty() {
            message.set("Invalid reset link. Please request a new password reset.".to_string());
            return;
        }

        if password().len() < 8 {
            message.set("Password must be at least 8 characters long".to_string());
            return;
        }

        if password() != confirm_password() {
            message.set("Passwords do not match".to_string());
            return;
        }

        is_loading.set(true);
        message.set(String::new());

        // Call Directus password reset API
        let client = reqwest::Client::new();
        let response = client
            .post("http://directus:8055/auth/password/reset")
            .header("Content-Type", "application/json")
            .body(format!("{{\"token\": \"{}\", \"password\": \"{}\"}}", token, password()))
            .send()
            .await;

        match response {
            Ok(resp) => {
                if resp.status().is_success() {
                    message.set("Password updated successfully! You can now log in.".to_string());
                } else {
                    message.set("Failed to update password. The link may have expired.".to_string());
                }
            }
            Err(_) => {
                message.set("Network error. Please try again.".to_string());
            }
        }

        is_loading.set(false);
    };

    rsx! {
        div {
            class: "min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8",
            div {
                class: "max-w-md w-full space-y-8",
                div {
                    div {
                        h2 {
                            class: "mt-6 text-center text-3xl font-extrabold text-gray-900",
                            "Set new password"
                        }
                        p {
                            class: "mt-2 text-center text-sm text-gray-600",
                            "Enter your new password below"
                        }
                    }

                    if !message().is_empty() {
                        div {
                            class: "mt-4 p-4 rounded-md {if message().contains(\"successfully\") {\"bg-green-50 text-green-800\"} else {\"bg-red-50 text-red-800\"}}",
                            "{message()}"
                        }
                    }

                    form {
                        class: "mt-8 space-y-6",
                        onsubmit: handle_submit,
                        div {
                            class: "rounded-md shadow-sm -space-y-px",
                            div {
                                label {
                                    class: "sr-only",
                                    r#for: "password",
                                    "New password"
                                }
                                input {
                                    id: "password",
                                    name: "password",
                                    r#type: "password",
                                    required: true,
                                    class: "appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm",
                                    placeholder: "New password",
                                    value: "{password()}",
                                    oninput: move |event| password.set(event.value())
                                }
                            }
                            div {
                                label {
                                    class: "sr-only",
                                    r#for: "confirm-password",
                                    "Confirm new password"
                                }
                                input {
                                    id: "confirm-password",
                                    name: "confirm-password",
                                    r#type: "password",
                                    required: true,
                                    class: "appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm",
                                    placeholder: "Confirm new password",
                                    value: "{confirm_password()}",
                                    oninput: move |event| confirm_password.set(event.value())
                                }
                            }
                        }

                        div {
                            button {
                                r#type: "submit",
                                disabled: is_loading() || token.is_empty(),
                                class: "group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white {if is_loading() || token.is_empty() {\"bg-gray-400\"} else {\"bg-indigo-600 hover:bg-indigo-700\"}} focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500",
                                if is_loading() {
                                    "Updating..."
                                } else if token.is_empty() {
                                    "Invalid reset link"
                                } else {
                                    "Update password"
                                }
                            }
                        }
                    }

                    div {
                        class: "text-center",
                        a {
                            class: "font-medium text-indigo-600 hover:text-indigo-500",
                            href: "/login",
                            "Back to sign in"
                        }
                    }
                }
            }
        }
    }
}