"""Gradio UI for the AI Agent."""

import asyncio
from typing import Any, Dict, List, Optional

import gradio as gr
import httpx

from src.config import get_settings
from src.logging_config import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)

settings = get_settings()


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
        metadata: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add memory via API."""
        params: Dict[str, Any] = {"text": text}
        if metadata:
            import json
            params["metadata"] = json.loads(metadata)
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
api_client = APIClient()


async def chat_with_agent(
    message: str,
    history: List[List[str]],
    use_memory: bool,
) -> tuple:
    """Chat with the AI agent."""
    if not message.strip():
        return "", history

    try:
        result = await api_client.chat(message, use_memory)

        # In a real implementation, this would call an LLM
        # For now, we return the constructed prompt
        response = f"**Prompt constructed:**\n\n```\n{result.get('prompt', 'No response')}\n```"

        history.append([message, response])
        return "", history

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        history.append([message, error_msg])
        return "", history


async def search_memories(query: str, top_k: int) -> str:
    """Search memories and format results."""
    if not query.strip():
        return "Please enter a search query."

    try:
        results = await api_client.search_memory(query, top_k)

        if not results:
            return "No matching memories found."

        formatted = []
        for i, result in enumerate(results, 1):
            score = result.get("score", 0)
            text = result.get("text", "")
            metadata = result.get("metadata", {})

            formatted.append(
                f"**{i}.** (Score: {score:.3f})\n"
                f"```\n{text[:500]}{'...' if len(text) > 500 else ''}\n```"
            )
            if metadata:
                formatted.append(f"*Metadata: {metadata}*")
            formatted.append("")

        return "\n".join(formatted)

    except Exception as e:
        return f"Error searching memories: {str(e)}"


async def add_new_memory(text: str, metadata: str) -> str:
    """Add a new memory."""
    if not text.strip():
        return "Please enter text to remember."

    try:
        result = await api_client.add_memory(text, metadata if metadata else None)
        return f"Memory added successfully! ID: {result.get('id')}"

    except Exception as e:
        return f"Error adding memory: {str(e)}"


async def get_stats() -> str:
    """Get memory statistics."""
    try:
        stats = await api_client.get_memory_stats()
        return f"""
**Memory Statistics:**

- Total Chunks: {stats.get('total_chunks', 0)}
- Embedding Model: {stats.get('embedding_model', 'N/A')}
- Embedding Dimension: {stats.get('embedding_dimension', 'N/A')}
- Vector Store: {stats.get('vector_store_path', 'N/A')}
        """.strip()

    except Exception as e:
        return f"Error getting stats: {str(e)}"


async def list_directus_records(collection: str, limit: int) -> str:
    """List records from Directus collection."""
    if not collection.strip():
        return "Please enter a collection name."

    try:
        records = await api_client.list_records(collection, limit)

        if not records:
            return f"No records found in collection '{collection}'."

        import json
        return f"```json\n{json.dumps(records, indent=2, default=str)}\n```"

    except Exception as e:
        return f"Error listing records: {str(e)}"


def create_ui() -> gr.Blocks:
    """Create the Gradio UI."""

    with gr.Blocks(
        title=f"{settings.app_name} - AI Agent",
        theme=gr.themes.Soft(),
        css="""
        .chatbot { height: 500px; }
        .input-box { min-height: 60px; }
        """,
    ) as demo:
        gr.Markdown(f"""
        # 🤖 {settings.app_name}

        **Version:** {settings.app_version} | **Environment:** {settings.app_env}

        An AI agent powered by FastAPI, FastMCP, Directus, and Cognee RAG.
        """)

        with gr.Tabs():
            # Chat Tab
            with gr.Tab("💬 Chat"):
                with gr.Row():
                    with gr.Column(scale=3):
                        chatbot = gr.Chatbot(
                            label="Conversation",
                            elem_classes=["chatbot"],
                        )
                        msg_input = gr.Textbox(
                            label="Your message",
                            placeholder="Type your message here...",
                            lines=2,
                            elem_classes=["input-box"],
                        )
                        with gr.Row():
                            send_btn = gr.Button("Send", variant="primary")
                            clear_btn = gr.Button("Clear")

                    with gr.Column(scale=1):
                        use_memory_cb = gr.Checkbox(
                            label="Use Memory",
                            value=True,
                            info="Include relevant context from memory",
                        )
                        gr.Markdown("""
                        **Tips:**
                        - Enable memory for context-aware responses
                        - The agent retrieves relevant information automatically
                        - Memories are stored for future interactions
                        """)

                send_btn.click(
                    fn=chat_with_agent,
                    inputs=[msg_input, chatbot, use_memory_cb],
                    outputs=[msg_input, chatbot],
                )
                msg_input.submit(
                    fn=chat_with_agent,
                    inputs=[msg_input, chatbot, use_memory_cb],
                    outputs=[msg_input, chatbot],
                )
                clear_btn.click(lambda: (None, []), outputs=[msg_input, chatbot])

            # Memory Tab
            with gr.Tab("🧠 Memory"):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### Search Memories")
                        search_query = gr.Textbox(
                            label="Search Query",
                            placeholder="Enter search terms...",
                        )
                        top_k_slider = gr.Slider(
                            minimum=1,
                            maximum=20,
                            value=5,
                            step=1,
                            label="Number of Results",
                        )
                        search_btn = gr.Button("Search", variant="primary")
                        search_results = gr.Markdown(label="Results")

                    with gr.Column():
                        gr.Markdown("### Add Memory")
                        memory_text = gr.Textbox(
                            label="Text to Remember",
                            placeholder="Enter information to store...",
                            lines=4,
                        )
                        memory_metadata = gr.Textbox(
                            label="Metadata (JSON)",
                            placeholder='{"key": "value"}',
                        )
                        add_btn = gr.Button("Add Memory", variant="primary")
                        add_result = gr.Markdown(label="Result")

                search_btn.click(
                    fn=search_memories,
                    inputs=[search_query, top_k_slider],
                    outputs=search_results,
                )
                add_btn.click(
                    fn=add_new_memory,
                    inputs=[memory_text, memory_metadata],
                    outputs=add_result,
                )

            # Stats Tab
            with gr.Tab("📊 Statistics"):
                stats_btn = gr.Button("Refresh Statistics", variant="primary")
                stats_output = gr.Markdown()

                stats_btn.click(fn=get_stats, outputs=stats_output)

            # Directus Tab
            with gr.Tab("🗄️ Directus"):
                with gr.Row():
                    with gr.Column():
                        collection_input = gr.Textbox(
                            label="Collection Name",
                            placeholder="e.g., messages, memory_chunks",
                        )
                        limit_slider = gr.Slider(
                            minimum=1,
                            maximum=500,
                            value=100,
                            step=10,
                            label="Limit",
                        )
                        list_btn = gr.Button("List Records", variant="primary")

                    records_output = gr.Markdown(label="Records")

                list_btn.click(
                    fn=list_directus_records,
                    inputs=[collection_input, limit_slider],
                    outputs=records_output,
                )

        gr.Markdown("""
        ---
        Built with FastAPI + FastMCP + Directus + Cognee | Deployed with Podman + Nginx
        """)

    return demo


def main():
    """Main entry point for Gradio UI."""
    demo = create_ui()

    demo.launch(
        server_name=settings.gradio_server_name,
        server_port=settings.gradio_server_port,
        share=False,
        show_error=True,
    )


if __name__ == "__main__":
    main()
