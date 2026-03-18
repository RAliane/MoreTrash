use dioxus::prelude::*;

#[component]
pub fn Home() -> Element {
    rsx! {
        div {
            class: "min-h-screen bg-gradient-to-br from-indigo-50 to-white",
            // Hero section
            div {
                class: "relative overflow-hidden",
                div {
                    class: "max-w-7xl mx-auto",
                    div {
                        class: "relative z-10 pb-8 bg-gradient-to-br from-indigo-50 to-white sm:pb-16 md:pb-20 lg:pb-28 xl:pb-32",
                        main {
                            class: "mt-10 mx-auto max-w-7xl px-4 sm:mt-12 sm:px-6 md:mt-16 lg:mt-20 lg:px-8 xl:mt-28",
                            div {
                                class: "sm:text-center lg:text-left",
                                h1 {
                                    class: "text-4xl tracking-tight font-extrabold text-gray-900 sm:text-5xl md:text-6xl",
                                    span {
                                        class: "block xl:inline",
                                        "AI-Powered"
                                    }
                                    span {
                                        class: "block text-indigo-600 xl:inline",
                                        "Matching Platform"
                                    }
                                }
                                p {
                                    class: "mt-3 text-base text-gray-500 sm:mt-5 sm:text-lg sm:max-w-xl sm:mx-auto md:mt-5 md:text-xl lg:mx-0",
                                    "Matchgorithm uses evolutionary algorithms to find optimal matches for your needs. Whether it's dating, business partnerships, or custom optimization problems, our platform delivers results."
                                }
                                div {
                                    class: "mt-5 sm:mt-8 sm:flex sm:justify-center lg:justify-start",
                                    div {
                                        class: "rounded-md shadow",
                                        a {
                                            class: "w-full flex items-center justify-center px-8 py-3 border border-transparent text-base font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 md:py-4 md:text-lg md:px-10",
                                            href: "/auth/sign-in",
                                            "Get Started"
                                        }
                                    }
                                    div {
                                        class: "mt-3 sm:mt-0 sm:ml-3",
                                        a {
                                            class: "w-full flex items-center justify-center px-8 py-3 border border-transparent text-base font-medium rounded-md text-indigo-700 bg-indigo-100 hover:bg-indigo-200 md:py-4 md:text-lg md:px-10",
                                            href: "/about",
                                            "Learn More"
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
            // Features section
            div {
                class: "py-12 bg-white",
                div {
                    class: "max-w-7xl mx-auto px-4 sm:px-6 lg:px-8",
                    div {
                        class: "lg:text-center",
                        h2 {
                            class: "text-base text-indigo-600 font-semibold tracking-wide uppercase",
                            "Features"
                        }
                        p {
                            class: "mt-2 text-3xl leading-8 font-extrabold tracking-tight text-gray-900 sm:text-4xl",
                            "Everything you need for perfect matches"
                        }
                        p {
                            class: "mt-4 max-w-2xl text-xl text-gray-500 lg:mx-auto",
                            "Our platform combines advanced AI algorithms with intuitive interfaces to deliver unparalleled matching capabilities."
                        }
                    }
                    div {
                        class: "mt-10",
                        dl {
                            class: "space-y-10 md:space-y-0 md:grid md:grid-cols-2 md:gap-x-8 md:gap-y-10",
                            div {
                                div {
                                    dt {
                                        class: "text-lg leading-6 font-medium text-gray-900",
                                        "Evolutionary Algorithms"
                                    }
                                    dd {
                                        class: "mt-2 text-base text-gray-500",
                                        "State-of-the-art genetic algorithms optimize matches based on your criteria."
                                    }
                                }
                            }
                            div {
                                div {
                                    dt {
                                        class: "text-lg leading-6 font-medium text-gray-900",
                                        "Real-time Processing"
                                    }
                                    dd {
                                        class: "mt-2 text-base text-gray-500",
                                        "Process matches instantly with our high-performance backend infrastructure."
                                    }
                                }
                            }
                            div {
                                div {
                                    dt {
                                        class: "text-lg leading-6 font-medium text-gray-900",
                                        "Customizable Criteria"
                                    }
                                    dd {
                                        class: "mt-2 text-base text-gray-500",
                                        "Define your own matching parameters and weight preferences."
                                    }
                                }
                            }
                            div {
                                div {
                                    dt {
                                        class: "text-lg leading-6 font-medium text-gray-900",
                                        "Secure & Private"
                                    }
                                    dd {
                                        class: "mt-2 text-base text-gray-500",
                                        "Your data is protected with enterprise-grade security measures."
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}