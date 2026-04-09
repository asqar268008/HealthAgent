from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.chat_models import ChatOllama
from functools import lru_cache

_embedding = None

@lru_cache
def get_embedding():
    global _embedding
    if _embedding is None:
        _embedding = HuggingFaceEmbeddings(
    model_name="BAAI/bge-base-en-v1.5",
    encode_kwargs={"normalize_embeddings": True},
)
    return _embedding

@lru_cache
def get_model():
    return ChatOllama(model="llama3", temperature=0.7, max_tokens=500)

