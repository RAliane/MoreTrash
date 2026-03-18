use dioxus::prelude::*;

#[component]
pub fn NavBar() -> Element {
    rsx! {
        nav {
            class: "bg-white shadow-lg",
            div {
                class: "max-w-7xl mx-auto px-4 sm:px-6 lg:px-8",
                div {
                    class: "flex justify-between h-16",
                    div {
                        class: "flex",
                        div {
                            class: "flex-shrink-0 flex items-center",
                            h1 {
                                class: "text-xl font-bold text-gray-900",
                                "Matchgorithm"
                            }
                        }
                        div {
                            class: "hidden sm:ml-6 sm:flex sm:space-x-8",
                            a {
                                class: "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium",
                                href: "/",
                                "Home"
                            }
                            a {
                                class: "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium",
                                href: "/matches",
                                "Matches"
                            }
                            a {
                                class: "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium",
                                href: "/dashboard",
                                "Dashboard"
                            }
                            a {
                                class: "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium",
                                href: "/admin",
                                "Admin"
                            }
                        }
                    }
                    div {
                        class: "hidden sm:ml-6 sm:flex sm:items-center",
                        div {
                            class: "ml-3 relative",
                            div {
                                button {
                                    r#type: "button",
                                    class: "bg-white flex text-sm rounded-full focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500",
                                    id: "user-menu-button",
                                    "aria-expanded": "false",
                                    "aria-haspopup": "true",
                                    img {
                                        class: "h-8 w-8 rounded-full",
                                        src: "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=facearea&facepad=2&w=256&h=256&q=80",
                                        alt: "User avatar"
                                    }
                                }
                            }
                        }
                        div {
                            class: "ml-3",
                            a {
                                class: "bg-indigo-600 hover:bg-indigo-700 text-white px-3 py-2 rounded-md text-sm font-medium",
                                href: "/login",
                                "Sign In"
                            }
                        }
                    }
                }
            }
        }
    }
}