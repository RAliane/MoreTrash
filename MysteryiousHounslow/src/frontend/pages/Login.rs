use dioxus::prelude::*;

#[component]
pub fn Login() -> Element {
    rsx! {
        div {
            class: "min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8",
            div {
                class: "max-w-md w-full space-y-8",
                div {
                    div {
                        h2 {
                            class: "mt-6 text-center text-3xl font-extrabold text-gray-900",
                            "Sign in to Matchgorithm"
                        }
                        p {
                            class: "mt-2 text-center text-sm text-gray-600",
                            "Enter your credentials to access your account"
                        }
                    }
                    form {
                        class: "mt-8 space-y-6",
                        onsubmit: |_| {}, // Placeholder for form submission
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
                                    class: "appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm",
                                    placeholder: "Email address"
                                }
                            }
                            div {
                                label {
                                    class: "sr-only",
                                    r#for: "password",
                                    "Password"
                                }
                                input {
                                    id: "password",
                                    name: "password",
                                    r#type: "password",
                                    required: true,
                                    class: "appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm",
                                    placeholder: "Password"
                                }
                            }
                        }

                        div {
                            class: "flex items-center justify-between",
                            div {
                                class: "flex items-center",
                                input {
                                    id: "remember-me",
                                    name: "remember-me",
                                    r#type: "checkbox",
                                    class: "h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                                }
                                label {
                                    class: "ml-2 block text-sm text-gray-900",
                                    r#for: "remember-me",
                                    "Remember me"
                                }
                            }

                            div {
                                class: "text-sm",
                                a {
                                    class: "font-medium text-indigo-600 hover:text-indigo-500",
                                    href: "/forgot-password",
                                    "Forgot your password?"
                                }
                            }
                        }

                        div {
                            button {
                                r#type: "submit",
                                class: "group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500",
                                "Sign in"
                            }
                        }

                        div {
                            class: "text-center",
                            p {
                                class: "text-sm text-gray-600",
                                "Don't have an account? "
                                a {
                                    class: "font-medium text-indigo-600 hover:text-indigo-500",
                                    href: "/register",
                                    "Sign up"
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}