"""Streamlit UI for the AI Agent."""

import asyncio
from typing import Any, Dict, List, Optional

import httpx
import streamlit as st

from src.config import get_settings
from src.logging_config import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)

settings = get_settings()

# Page configuration
st.set_page_config(
    page_title=f"{settings.app_name} - AI Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)


class APIClient:
    """Client for communicating with the FastAPI backend."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=30.0)

    async def health_check(self) -> Dict[str, Any]:
        """Check API health."""
        response = await self.client.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()

    async def chat(
        self,
        message: str,
        use_memory: bool = True,
    ) -> Dict[str, Any]:
        """Send chat message to API."""
        response = await self.client.post(
            f"{self.base_url}/api/chat",
            params={"message": message, "use_memory": use_memory},
        )
        response.raise_for_status()
        return response.json()

    async def search_memory(
        self,
        query: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Search memory via API."""
        response = await self.client.get(
            f"{self.base_url}/api/memory/search",
            params={"query": query, "top_k": top_k},
        )
        response.raise_for_status()
        return response.json()

    async def add_memory(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Add memory via API."""
        params: Dict[str, Any] = {"text": text}
        if metadata:
            params["metadata"] = metadata
        response = await self.client.post(
            f"{self.base_url}/api/memory",
            params=params,
        )
        response.raise_for_status()
        return response.json()

    async def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        response = await self.client.get(f"{self.base_url}/api/memory/stats")
        response.raise_for_status()
        return response.json()

    async def list_records(
        self,
        collection: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List records from a collection."""
        response = await self.client.get(
            f"{self.base_url}/api/collections/{collection}",
            params={"limit": limit},
        )
        response.raise_for_status()
        return response.json()

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Initialize API client
@st.cache_resource
def get_api_client() -> APIClient:
    return APIClient()


api_client = get_api_client()


def run_async(coro):
    """Run async function in sync context."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


def render_sidebar():
    """Render the sidebar."""
    with st.sidebar:
        st.title("🤖 AI Agent")
        st.markdown(f"**{settings.app_name}**")
        st.markdown(f"Version: `{settings.app_version}`")
        st.markdown(f"Environment: `{settings.app_env}`")

        st.divider()

        # API Status
        try:
            health = run_async(api_client.health_check())
            st.success("✅ API Connected")
            st.json(health)
        except Exception as e:
            st.error(f"❌ API Error: {e}")

        st.divider()

        st.markdown("""
        ### Quick Links
        - [API Docs](http://localhost:8000/docs)
        - [Health Check](http://localhost:8000/health)
        - [Metrics](http://localhost:8000/metrics)
        """)


def render_chat():
    """Render the chat interface."""
    st.header("💬 Chat with AI Agent")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    use_memory = st.checkbox("Use Memory Context", value=True)

    if prompt := st.chat_input("Type your message..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    result = run_async(api_client.chat(prompt, use_memory))
                    response = f"```\n{result.get('prompt', 'No response')}\n```"
                    st.markdown(response)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response,
                    })
                except Exception as e:
                    st.error(f"Error: {e}")


def render_memory():
    """Render the memory management interface."""
    st.header("🧠 Memory Management")

    tabs = st.tabs(["Search", "Add Memory", "Statistics"])

    with tabs[0]:
        st.subheader("Search Memories")
        query = st.text_input("Search Query", placeholder="Enter search terms...")
        top_k = st.slider("Number of Results", 1, 20, 5)

        if st.button("Search", type="primary"):
            if query:
                with st.spinner("Searching..."):
                    try:
                        results = run_async(api_client.search_memory(query, top_k))

                        if not results:
                            st.info("No matching memories found.")
                        else:
                            for i, result in enumerate(results, 1):
                                with st.expander(
                                    f"Result {i} (Score: {result.get('score', 0):.3f})"
                                ):
                                    st.text(result.get("text", ""))
                                    if result.get("metadata"):
                                        st.json(result["metadata"])
                    except Exception as e:
                        st.error(f"Error: {e}")
            else:
                st.warning("Please enter a search query.")

    with tabs[1]:
        st.subheader("Add New Memory")
        memory_text = st.text_area(
            "Text to Remember",
            placeholder="Enter information to store...",
            height=150,
        )
        metadata_json = st.text_area(
            "Metadata (JSON)",
            placeholder='{"key": "value"}',
        )

        if st.button("Add Memory", type="primary"):
            if memory_text:
                with st.spinner("Adding..."):
                    try:
                        import json
                        metadata = json.loads(metadata_json) if metadata_json else None
                        result = run_async(api_client.add_memory(memory_text, metadata))
                        st.success(f"Memory added! ID: {result.get('id')}")
                    except Exception as e:
                        st.error(f"Error: {e}")
            else:
                st.warning("Please enter text to remember.")

    with tabs[2]:
        st.subheader("Memory Statistics")

        if st.button("Refresh Statistics", type="primary"):
            with st.spinner("Loading..."):
                try:
                    stats = run_async(api_client.get_memory_stats())

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Chunks", stats.get("total_chunks", 0))
                    with col2:
                        st.metric("Embedding Dimension", stats.get("embedding_dimension", "N/A"))
                    with col3:
                        st.text(f"Model: {stats.get('embedding_model', 'N/A')}")

                    st.json(stats)
                except Exception as e:
                    st.error(f"Error: {e}")


def render_directus():
    """Render the Directus interface."""
    st.header("🗄️ Directus Data")

    col1, col2 = st.columns([1, 3])

    with col1:
        collection = st.text_input(
            "Collection Name",
            placeholder="e.g., messages",
        )
        limit = st.number_input("Limit", 1, 500, 100)

    if st.button("List Records", type="primary"):
        if collection:
            with st.spinner("Loading..."):
                try:
                    records = run_async(api_client.list_records(collection, limit))

                    if not records:
                        st.info(f"No records found in '{collection}'.")
                    else:
                        st.write(f"Found {len(records)} records:")
                        import pandas as pd

                        # Convert to DataFrame for better display
                        df = pd.json_normalize(records)
                        st.dataframe(df, use_container_width=True)

                        # Raw JSON view
                        with st.expander("Raw JSON"):
                            st.json(records)

                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.warning("Please enter a collection name.")


def main():
    """Main entry point for Streamlit UI."""
    st.title("🤖 AI Agent Dashboard")

    render_sidebar()

    # Main tabs
    tab_chat, tab_memory, tab_directus = st.tabs([
        "💬 Chat",
        "🧠 Memory",
        "🗄️ Directus",
    ])

    with tab_chat:
        render_chat()

    with tab_memory:
        render_memory()

    with tab_directus:
        render_directus()

    # Footer
    st.divider()
    st.markdown("""
    <div style="text-align: center; color: #666;">
        Built with FastAPI + FastMCP + Directus + Cognee | Deployed with Podman + Nginx
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
