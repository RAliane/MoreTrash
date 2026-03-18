use dioxus::prelude::*;

#[component]
pub fn ForgotPassword() -> Element {
    let mut email = use_signal(|| String::new());
    let mut message = use_signal(|| String::new());
    let mut is_loading = use_signal(|| false);

    let handle_submit = move |event: FormEvent| async move {
        event.prevent_default();

        if email().is_empty() {
            message.set("Please enter your email address".to_string());
            return;
        }

        is_loading.set(true);
        message.set(String::new());

        // Call Directus password reset API
        let client = reqwest::Client::new();
        let response = client
            .post("http://directus:8055/auth/password/request")
            .header("Content-Type", "application/json")
            .body(format!("{{\"email\": \"{}\"}}", email()))
            .send()
            .await;

        match response {
            Ok(resp) => {
                if resp.status().is_success() {
                    message.set("Password reset email sent! Check your inbox.".to_string());
                } else {
                    message.set("Failed to send reset email. Please try again.".to_string());
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
                            "Reset your password"
                        }
                        p {
                            class: "mt-2 text-center text-sm text-gray-600",
                            "Enter your email address and we'll send you a link to reset your password"
                        }
                    }

                    if !message().is_empty() {
                        div {
                            class: "mt-4 p-4 rounded-md {if message().contains(\"sent\") {\"bg-green-50 text-green-800\"} else {\"bg-red-50 text-red-800\"}}",
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
                                    r#for: "email",
                                    "Email address"
                                }
                                input {
                                    id: "email",
                                    name: "email",
                                    r#type: "email",
                                    required: true,
                                    class: "appearance-none rounded-md relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm",
                                    placeholder: "Email address",
                                    value: "{email()}",
                                    oninput: move |event| email.set(event.value())
                                }
                            }
                        }

                        div {
                            button {
                                r#type: "submit",
                                disabled: is_loading(),
                                class: "group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white {if is_loading() {\"bg-gray-400\"} else {\"bg-indigo-600 hover:bg-indigo-700\"}} focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500",
                                if is_loading() {
                                    "Sending..."
                                } else {
                                    "Send reset link"
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