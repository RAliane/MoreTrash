#from fastapi import FastAPI
import os
import anyio
from pprint import pprint
from pydantic import BaseModel
from directus_sdk_py import DirectusClient

#os.environ["LLM_API_KEY"] = "YOUR_OPENAI_KEY"

LLM_API_KEY="ollama"
LLM_MODEL="granite3.1-moe:3b"
LLM_POVIDER="ollama"
LLM_ENDPOINT="http://127.0.0.1:11434/v1"
EMBEDDING_MODEL="granite-embedding:latest"
EMBEDDING_ENDPOINT="http://127.0.0.1:11434/api/embeddings"
EMBEDDING_DIMENSIONS=512
HUGGINGFACE_TOKENIZER=""

client = DirectusClient(url="https://your-directus-instance.com",token="your_access_token")

client.login(email='user@example.com', password='password')

me = client.me()

client.refresh()

client.logout()



users = client.get_users()

"""
app = FastAPI()

# Get One Item
app.get

# Get more than one item (many)
app.get

# Post an update
app.post

# Put an update
app.put

# Patch a partial update
app.patch

# Delete something 
app.delete
"""

async def main():
    await cognee.add("Cognee turns documents into AI memory.")
    await cognee.cognify()
    await cognee.memify()
    results = await cognee.search("What does Cognee do?")
    for result in results:
        pprint(result)

