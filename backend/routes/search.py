"""Two-stage property search: SQL filter + vector similarity (fast), then LLM re-rank (separate call).
If the full filter set returns nothing, progressively drop secondary constraints before
falling back to pure similarity search — so one mismatched detail doesn't zero everything out.
"""
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from ai import extract_search_filters, generate_embedding, rerank_candidates
from db import get_pool

router = APIRouter(prefix="/search", tags=["search"])


class SearchRequest(BaseModel):
    query: str
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    bedrooms: Optional[int] = None
    location: Optional[str] = None
    property_type: Optional[str] = None
    amenities: Optional[list[str]] = None
    limit: int = 8


class CandidateOut(BaseModel):
    id: str
    title: str
    summary: str
    price: float
    bedrooms: int
    bathrooms: int
    location: str
    property_type: str
    amenities: list[str] = []
    balconies: Optional[int] = None
    parking_spots: Optional[int] = None
    area_sqft: Optional[int] = None
    facing: Optional[str] = None
    building_height_type: Optional[str] = None
    handover_status: Optional[str] = None
    handover_date: Optional[str] = None


class SearchResponse(BaseModel):
    candidates: list[CandidateOut]
    relaxed_filters: list[str] = []


class RerankRequest(BaseModel):
    query: str
    candidate_ids: list[str]


class RerankedResult(BaseModel):
    id: str
    reason: str


class RerankResponse(BaseModel):
    results: list[RerankedResult]


SELECT_COLUMNS = """
    id, title, summary, price, bedrooms, bathrooms, location, property_type,
    amenities, balconies, parking_spots, area_sqft, facing,
    building_height_type, handover_status, handover_date
"""

RELAX_ORDER = [
    "amenities", "facing", "building_type", "handover_status", "handover_date",
    "area", "parking", "balconies", "property_type", "location", "bedrooms", "price",
]


async def _run_query(pool, active: list[tuple[str, str, object]], query_embedding, limit):
    params: list = []
    where_parts = []
    for _name, sql_template, value in active:
        params.append(value)
        where_parts.append(sql_template.format(idx=f"${len(params)}"))

    where_clause = f"where {' and '.join(where_parts)}" if where_parts else ""
    params.append(query_embedding)
    embedding_param = f"${len(params)}"
    params.append(limit)
    limit_param = f"${len(params)}"

    sql = f"""
        select {SELECT_COLUMNS} from properties
        {where_clause}
        order by embedding <=> {embedding_param}
        limit {limit_param}
    """
    return await pool.fetch(sql, *params)


@router.post("", response_model=SearchResponse)
async def search_properties(req: SearchRequest):
    pool = get_pool()

    try:
        extracted = await extract_search_filters(req.query)
    except Exception:
        extracted = {}

    min_price = req.min_price if req.min_price is not None else extracted.get("min_price")
    max_price = req.max_price if req.max_price is not None else extracted.get("max_price")
    location = req.location or extracted.get("location")
    property_type = req.property_type or extracted.get("property_type")
    amenities = list(set((req.amenities or []) + extracted.get("amenities", [])))

    all_conditions: list[tuple[str, str, object]] = []
    if min_price is not None:
        all_conditions.append(("price", "price >= {idx}", min_price))
    if max_price is not None:
        all_conditions.append(("price", "price <= {idx}", max_price))
    if location:
        all_conditions.append(("location", "location ilike {idx}", f"%{location}%"))
    if property_type:
        all_conditions.append(("property_type", "property_type = {idx}", property_type))
    if amenities:
        all_conditions.append(("amenities", "amenities @> {idx}::text[]", amenities))

    if extracted.get("min_balconies") is not None:
        all_conditions.append(("balconies", "balconies >= {idx}", extracted["min_balconies"]))
    if extracted.get("max_balconies") is not None:
        all_conditions.append(("balconies", "balconies <= {idx}", extracted["max_balconies"]))
    if extracted.get("min_parking") is not None:
        all_conditions.append(("parking", "parking_spots >= {idx}", extracted["min_parking"]))
    if extracted.get("max_parking") is not None:
        all_conditions.append(("parking", "parking_spots <= {idx}", extracted["max_parking"]))
    if extracted.get("min_area_sqft") is not None:
        all_conditions.append(("area", "area_sqft >= {idx}", extracted["min_area_sqft"]))
    if extracted.get("max_area_sqft") is not None:
        all_conditions.append(("area", "area_sqft <= {idx}", extracted["max_area_sqft"]))
    if extracted.get("facing"):
        all_conditions.append(("facing", "facing = {idx}", extracted["facing"]))
    if extracted.get("building_height_type"):
        all_conditions.append(("building_type", "building_height_type = {idx}", extracted["building_height_type"]))
    if extracted.get("handover_status"):
        all_conditions.append(("handover_status", "handover_status = {idx}", extracted["handover_status"]))
    if extracted.get("min_handover_date"):
        all_conditions.append(("handover_date", "handover_date >= {idx}::date", extracted["min_handover_date"]))
    if extracted.get("max_handover_date"):
        all_conditions.append(("handover_date", "handover_date <= {idx}::date", extracted["max_handover_date"]))

    if req.bedrooms is not None:
        all_conditions.append(("bedrooms", "bedrooms >= {idx}", req.bedrooms))
    elif extracted.get("bedrooms") is not None:
        all_conditions.append(("bedrooms", "bedrooms = {idx}", extracted["bedrooms"]))

    query_embedding = await generate_embedding(req.query)

    relaxed: list[str] = []
    active = list(all_conditions)
    rows = await _run_query(pool, active, query_embedding, req.limit)

    for drop_name in RELAX_ORDER:
        if rows:
            break
        if not any(name == drop_name for name, _, _ in active):
            continue
        active = [c for c in active if c[0] != drop_name]
        relaxed.append(drop_name)
        rows = await _run_query(pool, active, query_embedding, req.limit)

    return SearchResponse(
        candidates=[
            CandidateOut(
                id=str(r["id"]), title=r["title"], summary=r["summary"],
                price=r["price"], bedrooms=r["bedrooms"], bathrooms=r["bathrooms"],
                location=r["location"], property_type=r["property_type"],
                amenities=r["amenities"], balconies=r["balconies"], parking_spots=r["parking_spots"],
                area_sqft=r["area_sqft"], facing=r["facing"],
                building_height_type=r["building_height_type"], handover_status=r["handover_status"],
                handover_date=str(r["handover_date"]) if r["handover_date"] else None,
            )
            for r in rows
        ],
        relaxed_filters=relaxed,
    )


@router.post("/rerank", response_model=RerankResponse)
async def rerank_search_results(req: RerankRequest):
    pool = get_pool()
    rows = await pool.fetch(
        "select id, summary from properties where id = any($1::uuid[])",
        req.candidate_ids,
    )
    candidates = [{"id": str(r["id"]), "summary": r["summary"]} for r in rows]
    ranked = await rerank_candidates(req.query, candidates)
    return RerankResponse(results=[RerankedResult(id=r["id"], reason=r["reason"]) for r in ranked])