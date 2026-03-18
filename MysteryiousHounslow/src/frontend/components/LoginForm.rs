use dioxus::prelude::*;

#[component]
pub fn LoginForm() -> Element {
    rsx! {
        form {
            class: "space-y-4",
            onsubmit: |_| {}, // Placeholder for form submission
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
                    placeholder: "Enter your password"
                }
            }
            button {
                r#type: "submit",
                class: "w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500",
                "Sign In"
            }
        }
    }
}