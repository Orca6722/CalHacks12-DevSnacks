import json
import os
from typing import List, Dict
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from .settings import CHROMA_DB_DIR, USER_ID

# Persistent client
_client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
_embed = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

MENUS = "menus"
PREFS = "prefs"
COMMITS = "commits"


def get_collection(name: str):
    try:
        col = _client.get_collection(name)
    except Exception:
        col = _client.create_collection(name=name, embedding_function=_embed)
    return col


def ensure_collections():
    for name in (MENUS, PREFS, COMMITS):
        try:
            _client.get_collection(name)
        except Exception:
            _client.create_collection(name=name, embedding_function=_embed)


def add_menus(items: List[Dict]):
    col = get_collection(MENUS)
    ids = [it["id"] for it in items]
    docs = [f"{it['name']} — {it['description']} — tags: {','.join(json.loads(it['tags']))}"
            for it in items]
    metas = [
        {
            "price": float(it["price"]),
            "cuisine": it["cuisine"],
            "dietary": json.loads(it["dietary"]),
            "eta": int(it["eta_min"]),
            "restaurant": it["restaurant"],
            "name": it["name"],
        }
        for it in items
    ]
    col.add(ids=ids, documents=docs, metadatas=metas)


def query_menus(query_text: str, k: int = 12):
    col = get_collection(MENUS)
    res = col.query(query_texts=[query_text], n_results=k)
    # Return flattened list
    out = []
    if res and res.get("ids"):
        for i, mid in enumerate(res["ids"][0]):
            meta = res["metadatas"][0][i]
            out.append({
                "id": mid,
                "name": meta.get("name"),
                "price": meta.get("price"),
                "eta": meta.get("eta"),
                "dietary": meta.get("dietary", []),
                "restaurant": meta.get("restaurant"),
            })
    return out


def add_feedback(user_id: str, item_id: str, liked: bool, notes: str | None = None):
    col = get_collection(PREFS)
    col.add(ids=[f"{user_id}:{item_id}:{liked}"],
            documents=[f"{'likes' if liked else 'dislikes'}: {item_id} {notes or ''}"],
            metadatas=[{"userId": user_id, "itemId": item_id, "liked": liked}])


def rerank_with_prefs(candidates: List[Dict], user_id: str, alpha: float = 0.85):
    """Very simple personalization: boost items similar to liked prefs and down-weight those similar to dislikes."""
    pref_col = get_collection(PREFS)
    if not candidates:
        return []
    # Build a query per item name to get a similarity proxy via chroma (hacky but fine for demo)
    scored = []
    for it in candidates:
        name = it["name"]
        # Similarity to liked
        like_res = pref_col.query(query_texts=[f"likes: {name}"], where={"liked": True}, n_results=1)
        like_score = 1.0 if like_res.get("ids") else 0.0
        # Similarity to disliked
        dislike_res = pref_col.query(query_texts=[f"dislikes: {name}"], where={"liked": False}, n_results=1)
        dislike_score = 1.0 if dislike_res.get("ids") else 0.0
        score = alpha * (1 + like_score) - (1 - alpha) * (1 + dislike_score)
        scored.append((score, it))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [it for _, it in scored]