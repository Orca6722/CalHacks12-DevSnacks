# shared/chroma_client.py
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

# Swap model as needed; 'all-MiniLM-L6-v2' is light and fine for hackathon
emb_fn = SentenceTransformerEmbeddingFunction(model_name="sentence-transformers/all-MiniLM-L6-v2")

client = chromadb.Client()            # for local dev; switch to persistent server if you want
collection = client.get_or_create_collection(
    name="commit_moods",
    embedding_function=emb_fn         # Chroma will call this for you
)
