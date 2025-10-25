# agents/mood_embedder/main.py
import os
from uagents import Agent, Context, Protocol
from groq import Groq
from shared.schemas import EmbedCommitRequest, EmbedCommitResponse
from shared.chroma_client import collection

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY)

proto = Protocol("mood-embedder", version="1.0.0")

MOOD_SYS = (
    "You label developer commit messages with a single lowercase mood token "
    "from this set: [focused, energized, meh, stressed, celebratory, calm]. "
    "Return ONLY the token."
)

@proto.on_message(EmbedCommitRequest, replies=EmbedCommitResponse)
async def handle_embed(ctx: Context, msg: EmbedCommitRequest):
    # 1) Mood classification via Groq LLM (chat completion)
    text = f"Commit message: {msg.commit.message}"
    comp = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",   # pick a Groq-supported model you prefer
        messages=[{"role":"system","content":MOOD_SYS},
                  {"role":"user","content":text}],
        temperature=0.2,
        max_tokens=5,
    )
    mood = comp.choices[0].message.content.strip().split()[0]

    # 2) Upsert into Chroma (Chroma will auto-embed using our embedding_function)
    doc_id = msg.commit.sha
    metadata = {
        "sha": msg.commit.sha,
        "author": msg.commit.author,
        "date_iso": msg.commit.date_iso,
        "mood": mood,
    }
    collection.add(ids=[doc_id], documents=[msg.commit.message], metadatas=[metadata])

    await ctx.send(ctx.sender, EmbedCommitResponse(id=doc_id, mood_label=mood, vector_dim=collection._embedding_function.dim))  # type: ignore

agent = Agent(name="mood_embedder", seed=os.getenv("SEED", "mood-embedder-seed"))
agent.include(proto)

if __name__ == "__main__":
    agent.run()
