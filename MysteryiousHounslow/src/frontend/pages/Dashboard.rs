use dioxus::prelude::*;

#[component]
pub fn Dashboard() -> Element {
    rsx! {
        div {
            class: "min-h-screen bg-gray-50",
            div {
                class: "max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8",
                h1 {
                    class: "text-3xl font-bold text-gray-900",
                    "Dashboard"
                }
                p {
                    class: "mt-2 text-sm text-gray-600",
                    "Welcome to your personal dashboard. This is where you can manage your matching preferences and view results."
                }
                div {
                    class: "mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3",
                    // Placeholder cards for dashboard sections
                    div {
                        class: "bg-white overflow-hidden shadow rounded-lg",
                        div {
                            class: "p-5",
                            div {
                                class: "flex items-center",
                                div {
                                    class: "flex-shrink-0",
                                    // Placeholder icon
                                    div {
                                        class: "w-8 h-8 bg-indigo-500 rounded-full"
                                    }
                                }
                                div {
                                    class: "ml-5 w-0 flex-1",
                                    dl {
                                        dt {
                                            class: "text-sm font-medium text-gray-500 truncate",
                                            "Matching Algorithm"
                                        }
                                        dd {
                                            class: "text-lg font-medium text-gray-900",
                                            "Status: Placeholder"
                                        }
                                    }
                                }
                            }
                        }
                        div {
                            class: "bg-gray-50 px-5 py-3",
                            div {
                                class: "text-sm",
                                a {
                                    class: "font-medium text-indigo-600 hover:text-indigo-500",
                                    href: "#",
                                    "View details"
                                }
                            }
                        }
                    }
                    div {
                        class: "bg-white overflow-hidden shadow rounded-lg",
                        div {
                            class: "p-5",
                            div {
                                class: "flex items-center",
                                div {
                                    class: "flex-shrink-0",
                                    div {
                                        class: "w-8 h-8 bg-green-500 rounded-full"
                                    }
                                }
                                div {
                                    class: "ml-5 w-0 flex-1",
                                    dl {
                                        dt {
                                            class: "text-sm font-medium text-gray-500 truncate",
                                            "Analytics"
                                        }
                                        dd {
                                            class: "text-lg font-medium text-gray-900",
                                            "Coming Soon"
                                        }
                                    }
                                }
                            }
                        }
                        div {
                            class: "bg-gray-50 px-5 py-3",
                            div {
                                class: "text-sm",
                                a {
                                    class: "font-medium text-indigo-600 hover:text-indigo-500",
                                    href: "#",
                                    "View analytics"
                                }
                            }
                        }
                    }
                    div {
                        class: "bg-white overflow-hidden shadow rounded-lg",
                        div {
                            class: "p-5",
                            div {
                                class: "flex items-center",
                                div {
                                    class: "flex-shrink-0",
                                    div {
                                        class: "w-8 h-8 bg-yellow-500 rounded-full"
                                    }
                                }
                                div {
                                    class: "ml-5 w-0 flex-1",
                                    dl {
                                        dt {
                                            class: "text-sm font-medium text-gray-500 truncate",
                                            "Profile Settings"
                                        }
                                        dd {
                                            class: "text-lg font-medium text-gray-900",
                                            "Not Implemented"
                                        }
                                    }
                                }
                            }
                        }
                        div {
                            class: "bg-gray-50 px-5 py-3",
                            div {
                                class: "text-sm",
                                a {
                                    class: "font-medium text-indigo-600 hover:text-indigo-500",
                                    href: "#",
                                    "Update profile"
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}