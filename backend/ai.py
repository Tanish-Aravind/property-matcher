"""Single AI client wrapper: brochure summarization, field extraction, embeddings, and re-rank.
Provider (gemini | openai) is swappable via AI_PROVIDER env var.
"""
import json
import os
from typing import Any

AI_PROVIDER = os.environ.get("AI_PROVIDER", "gemini")

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
GEMINI_EMBED_MODEL = "gemini-embedding-001"
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_EMBED_MODEL = "text-embedding-3-small"

AMENITIES_LIST = [
    "swimming pool", "gym", "clubhouse", "balcony", "covered parking",
    "garden", "power backup", "security", "lift", "children's play area",
    "gated community", "modular kitchen", "servant room", "jogging track", "terrace",
    "walk-in wardrobe",
]

FACING_OPTIONS = ["north", "south", "east", "west", "north_east", "north_west", "south_east", "south_west"]
BUILDING_HEIGHT_OPTIONS = ["low_rise", "high_rise"]
HANDOVER_STATUS_OPTIONS = ["ready_to_move", "under_construction"]

SUMMARY_SYSTEM_PROMPT = (
    "You are a real estate assistant. Given raw brochure text, write a concise ~150 word "
    "summary covering: property type, location, price, bedrooms, bathrooms, key features, "
    "and standout selling points. Plain prose, no headers or bullet points."
)

EXTRACT_SYSTEM_PROMPT = (
    "You are a real estate data extraction assistant. Given raw brochure text, extract "
    "structured property details. Respond ONLY with JSON, no markdown fences, no prose, "
    "matching exactly this shape:\n"
    '{"title": string, "price": number, "bedrooms": integer, "bathrooms": integer, '
    '"location": string, "property_type": string, "amenities": array of strings, '
    '"balconies": integer or null, "parking_spots": integer or null, '
    '"area_sqft": integer or null, "facing": string or null, '
    '"building_height_type": string or null, "handover_status": string or null, '
    '"handover_date": string or null}\n'
    "Rules: price is a plain number (no symbols/commas). property_type must be one of: "
    "apartment, house, villa, plot. title is a short human-readable name. location is the "
    "neighbourhood/area/city mentioned. amenities must ONLY contain items from this exact "
    f"list, exact spelling, only ones actually mentioned (empty list if none): {AMENITIES_LIST}. "
    "balconies, parking_spots, and area_sqft are numbers — only set them if the brochure "
    "states an actual figure; use null if not mentioned (do not guess these). facing must be "
    f"one of exactly: {FACING_OPTIONS} — only set if the brochure explicitly states a facing "
    "direction, else null. building_height_type must be one of exactly: "
    f"{BUILDING_HEIGHT_OPTIONS} — infer from context if the brochure mentions floor count or "
    "describes it as a tower/high-rise vs a low-rise/villa-style building; use null if truly "
    f"unclear. handover_status must be one of exactly: {HANDOVER_STATUS_OPTIONS} — 'ready to "
    "move', 'immediate possession' etc means ready_to_move; any future possession/completion "
    "date or 'under construction' means under_construction; use null if not mentioned at all. "
    "handover_date is only relevant when handover_status is under_construction — convert any "
    "stated date/quarter/month to YYYY-MM-DD format (use the 1st of the month if only "
    "month+year given, e.g. 'Dec 2027' -> '2027-12-01', 'Q4 2027' -> '2027-10-01'); null if "
    "ready_to_move or no date given. For all other fields (not the ones told to use null when "
    "unmentioned), make the most reasonable inference from context rather than leaving null."
)

SEARCH_FILTER_SYSTEM_PROMPT = (
    "You are a real estate search assistant. Given a client's natural language property "
    "request, extract any explicit hard constraints mentioned. Respond ONLY with JSON, no "
    "markdown fences, no prose, matching exactly this shape (use null for anything not "
    "mentioned, [] for amenities if none):\n"
    '{"bedrooms": integer or null, "min_price": number or null, "max_price": number or null, '
    '"location": string or null, "property_type": string or null, "amenities": array of strings, '
    '"min_balconies": integer or null, "max_balconies": integer or null, '
    '"min_parking": integer or null, "max_parking": integer or null, '
    '"min_area_sqft": integer or null, "max_area_sqft": integer or null, '
    '"facing": string or null, "building_height_type": string or null, '
    '"handover_status": string or null, "max_handover_date": string or null, '
    '"min_handover_date": string or null}\n'
    "Rules: bedrooms is an exact count from '3BHK'/'3 bedroom' etc. Prices are in Indian "
    "Rupees; convert lakh/crore (1 lakh=100000, 1 crore=10000000) — 'under 4cr' means "
    "max_price: 40000000. 'less than X'/'under X'/'below X' -> the 'max_' field; 'more than X'/"
    "'above X'/'over X' -> the 'min_' field; a plain count with no comparison word (e.g. '2 "
    "balconies') sets BOTH min and max to that same number (exact match). Apply this identical "
    "comparison logic to balconies, parking, and area_sqft (sqft/square feet mentions). "
    "property_type is one of: apartment, house, villa, plot — only if explicit. location is "
    "any area/city mentioned. amenities must ONLY contain items from this exact list, exact "
    f"spelling, only ones explicitly requested (walk-in wardrobe counts as an amenity): "
    f"{AMENITIES_LIST}. facing must be one of exactly: {FACING_OPTIONS} — only if the client "
    "explicitly says a direction like 'east facing'. building_height_type must be one of "
    f"exactly: {BUILDING_HEIGHT_OPTIONS} — only if client explicitly says 'low rise'/'high "
    f"rise'/'tower'. handover_status must be one of exactly: {HANDOVER_STATUS_OPTIONS} — set "
    "ready_to_move if client wants immediate possession, under_construction if they're fine "
    "waiting or specifically ask for upcoming/new projects; leave null if not mentioned. "
    "max_handover_date/min_handover_date: convert any date/quarter/year mentioned (e.g. "
    "'possession by 2027', 'handover before Dec 2028') to YYYY-MM-DD, using the same lack/more "
    "logic as price ('by X'/'before X' -> max_handover_date; 'after X' -> min_handover_date). "
    "Leave any field null/empty if the client's request doesn't mention it at all."
)

RERANK_SYSTEM_PROMPT = (
    "You are a real estate matching assistant. Given a client's request and a list of "
    "candidate property summaries, rank the candidates best-to-worst match for the client "
    "and give a one-line reason for each. Respond ONLY with JSON: a list of objects with "
    'keys "id" (matching the candidate id given) and "reason" (one short sentence). '
    "No prose, no markdown fences, just the JSON list."
)


def _gemini_client():
    import google.generativeai as genai
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    return genai


def _openai_client():
    from openai import OpenAI
    return OpenAI(api_key=os.environ["OPENAI_API_KEY"])


def _strip_json_fences(raw: str) -> str:
    return raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()


async def generate_summary(brochure_text: str) -> str:
    if AI_PROVIDER == "gemini":
        genai = _gemini_client()
        model = genai.GenerativeModel(GEMINI_MODEL, system_instruction=SUMMARY_SYSTEM_PROMPT)
        response = model.generate_content(brochure_text)
        return response.text.strip()
    else:
        client = _openai_client()
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
                {"role": "user", "content": brochure_text},
            ],
        )
        return response.choices[0].message.content.strip()


async def extract_property_fields(brochure_text: str) -> dict[str, Any]:
    if AI_PROVIDER == "gemini":
        genai = _gemini_client()
        model = genai.GenerativeModel(GEMINI_MODEL, system_instruction=EXTRACT_SYSTEM_PROMPT)
        response = model.generate_content(brochure_text)
        raw = response.text.strip()
    else:
        client = _openai_client()
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": EXTRACT_SYSTEM_PROMPT},
                {"role": "user", "content": brochure_text},
            ],
        )
        raw = response.choices[0].message.content.strip()

    fields = json.loads(_strip_json_fences(raw))

    required = {"title", "price", "bedrooms", "bathrooms", "location", "property_type"}
    missing = required - fields.keys()
    if missing:
        raise ValueError(f"AI extraction missing fields: {missing}")

    fields["amenities"] = [a for a in fields.get("amenities", []) if a in AMENITIES_LIST]
    fields["balconies"] = fields.get("balconies")
    fields["parking_spots"] = fields.get("parking_spots")
    fields["area_sqft"] = fields.get("area_sqft")
    fields["facing"] = fields.get("facing") if fields.get("facing") in FACING_OPTIONS else None
    fields["building_height_type"] = (
        fields.get("building_height_type") if fields.get("building_height_type") in BUILDING_HEIGHT_OPTIONS else None
    )
    fields["handover_status"] = (
        fields.get("handover_status") if fields.get("handover_status") in HANDOVER_STATUS_OPTIONS else None
    )
    fields["handover_date"] = fields.get("handover_date")

    return fields


async def extract_search_filters(query: str) -> dict[str, Any]:
    if AI_PROVIDER == "gemini":
        genai = _gemini_client()
        model = genai.GenerativeModel(GEMINI_MODEL, system_instruction=SEARCH_FILTER_SYSTEM_PROMPT)
        response = model.generate_content(query)
        raw = response.text.strip()
    else:
        client = _openai_client()
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SEARCH_FILTER_SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ],
        )
        raw = response.choices[0].message.content.strip()

    parsed = json.loads(_strip_json_fences(raw))
    parsed["amenities"] = [a for a in parsed.get("amenities", []) if a in AMENITIES_LIST]
    if parsed.get("facing") not in FACING_OPTIONS:
        parsed["facing"] = None
    if parsed.get("building_height_type") not in BUILDING_HEIGHT_OPTIONS:
        parsed["building_height_type"] = None
    if parsed.get("handover_status") not in HANDOVER_STATUS_OPTIONS:
        parsed["handover_status"] = None
    return parsed


async def generate_embedding(text: str) -> list[float]:
    if AI_PROVIDER == "gemini":
        genai = _gemini_client()
        result = genai.embed_content(
            model=f"models/{GEMINI_EMBED_MODEL}", content=text, output_dimensionality=768,
        )
        return result["embedding"]
    else:
        client = _openai_client()
        response = client.embeddings.create(model=OPENAI_EMBED_MODEL, input=text)
        return response.data[0].embedding


async def rerank_candidates(query: str, candidates: list[dict[str, Any]]) -> list[dict[str, str]]:
    candidates_block = "\n".join(f'- id: {c["id"]}\n  summary: {c["summary"]}' for c in candidates)
    user_prompt = f"Client request: {query}\n\nCandidates:\n{candidates_block}"

    if AI_PROVIDER == "gemini":
        genai = _gemini_client()
        model = genai.GenerativeModel(GEMINI_MODEL, system_instruction=RERANK_SYSTEM_PROMPT)
        response = model.generate_content(user_prompt)
        raw = response.text.strip()
    else:
        client = _openai_client()
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": RERANK_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
        raw = response.choices[0].message.content.strip()

    return json.loads(_strip_json_fences(raw))