use dioxus::prelude::*;

#[component]
pub fn AuthLayout(children: Element) -> Element {
    rsx! {
        div {
            class: "min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8",
            div {
                class: "max-w-md w-full space-y-8",
                div {
                    div {
                        h2 {
                            class: "mt-6 text-center text-3xl font-extrabold text-gray-900",
                            "Sign in to your account"
                        }
                        p {
                            class: "mt-2 text-center text-sm text-gray-600",
                            "Or "
                            a {
                                class: "font-medium text-indigo-600 hover:text-indigo-500",
                                href: "/auth/sign-up",
                                "create a new account"
                            }
                        }
                    }
                    {children}
                }
            }
        }
    }
}