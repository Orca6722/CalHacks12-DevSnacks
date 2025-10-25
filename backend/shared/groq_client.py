from groq import Groq
from .settings import GROQ_API_KEY

_client = None

def get_groq():
    global _client
    if _client is None:
        if not GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY missing. Set it in .env")
        _client = Groq(api_key=GROQ_API_KEY)
    return _client

MOOD_SYS_PROMPT = (
    "You analyze Git commit messages to infer the coder's mood and food preferences."
    " Return strict JSON with keys: mood, energy (low|med|high), valence (negative|neutral|positive),"
    " diet (keywords like 'light+protein' or 'comfort' or 'budget'), budget (number), spice (low|med|high),"
    " time ('morning'|'afternoon'|'evening'|'late-night'), and a natural-language retrieval query 'query'"
    " to search a food menu vector DB that matches the mood, diet, budget, spice, and time."
)

MOOD_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "mood": {"type": "string"},
        "energy": {"type": "string"},
        "valence": {"type": "string"},
        "diet": {"type": "string"},
        "budget": {"type": "number"},
        "spice": {"type": "string"},
        "time": {"type": "string"},
        "query": {"type": "string"}
    },
    "required": ["mood","energy","valence","diet","budget","spice","time","query"]
}

def extract_mood_json(commits: list[str]) -> dict:
    client = get_groq()
    text = "\n".join(commits[:40])
    # Use JSON mode by instructing the model clearly; Groq supports tool-like structured outputs
    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",  # choose a fast Groq model available to you
        messages=[
            {"role": "system", "content": MOOD_SYS_PROMPT},
            {"role": "user", "content": f"Analyze these commit messages and return JSON only:\n{text}"}
        ],
        temperature=0.3,
        max_tokens=350,
    )
    content = resp.choices[0].message.content
    # Be defensive: if the model wrapped JSON with code fences, strip
    import json, re
    match = re.search(r"\{[\s\S]*\}", content)
    if match:
        content = match.group(0)
    return json.loads(content)


def explain_choice(mood_json: dict, item_name: str) -> str:
    client = get_groq()
    prompt = (
        f"User mood: {mood_json}. In ONE short sentence, explain why '{item_name}' fits this mood and constraints."
        " Avoid fluff; be specific (e.g., 'light protein, low spice, late-night friendly')."
    )
    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=50,
    )
    return resp.choices[0].message.content.strip()