"""Two-step upload:
 1) POST /properties/extract  - PDF -> AI extracts fields + summary (nothing stored yet)
 2) POST /properties/confirm  - agent-reviewed fields + summary + re-sent PDF -> embed -> store
PATCH /properties/{id} for correcting a saved listing.
"""
import os
import uuid
from typing import Optional
from datetime import date as date_type
from fastapi import APIRouter, Form, HTTPException, UploadFile
from pydantic import BaseModel

from ai import extract_property_fields, generate_embedding, generate_summary
from db import get_pool
from pdf_extract import extract_text_from_pdf

router = APIRouter(prefix="/properties", tags=["properties"])


class ExtractedFields(BaseModel):
    title: str
    price: float
    bedrooms: int
    bathrooms: int
    location: str
    property_type: str
    summary: str
    amenities: list[str] = []
    balconies: Optional[int] = None
    parking_spots: Optional[int] = None
    area_sqft: Optional[int] = None
    facing: Optional[str] = None
    building_height_type: Optional[str] = None
    handover_status: Optional[str] = None
    handover_date: Optional[str] = None


class PropertyOut(BaseModel):
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


class PropertyUpdate(BaseModel):
    title: Optional[str] = None
    price: Optional[float] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    location: Optional[str] = None
    property_type: Optional[str] = None
    amenities: Optional[list[str]] = None
    balconies: Optional[int] = None
    parking_spots: Optional[int] = None
    area_sqft: Optional[int] = None
    facing: Optional[str] = None
    building_height_type: Optional[str] = None
    handover_status: Optional[str] = None
    handover_date: Optional[str] = None


def _row_to_out(row) -> PropertyOut:
    return PropertyOut(
        id=str(row["id"]), title=row["title"], summary=row["summary"],
        price=row["price"], bedrooms=row["bedrooms"], bathrooms=row["bathrooms"],
        location=row["location"], property_type=row["property_type"],
        amenities=row["amenities"], balconies=row["balconies"], parking_spots=row["parking_spots"],
        area_sqft=row["area_sqft"], facing=row["facing"],
        building_height_type=row["building_height_type"], handover_status=row["handover_status"],
        handover_date=str(row["handover_date"]) if row["handover_date"] else None,
    )


@router.post("/extract", response_model=ExtractedFields)
async def extract_property(brochure: UploadFile = None):
    if brochure is None:
        raise HTTPException(status_code=400, detail="brochure PDF file is required")
    if brochure.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="brochure must be a PDF")

    file_bytes = await brochure.read()

    try:
        brochure_text = extract_text_from_pdf(file_bytes)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    try:
        fields = await extract_property_fields(brochure_text)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not extract property details from PDF: {e}")

    summary = await generate_summary(brochure_text)

    return ExtractedFields(
        title=fields["title"], price=fields["price"], bedrooms=fields["bedrooms"],
        bathrooms=fields["bathrooms"], location=fields["location"],
        property_type=fields["property_type"], summary=summary,
        amenities=fields.get("amenities", []),
        balconies=fields.get("balconies"), parking_spots=fields.get("parking_spots"),
        area_sqft=fields.get("area_sqft"), facing=fields.get("facing"),
        building_height_type=fields.get("building_height_type"),
        handover_status=fields.get("handover_status"), handover_date=fields.get("handover_date"),
    )


@router.post("/confirm", response_model=PropertyOut)
async def confirm_property(
    title: str = Form(...),
    price: float = Form(...),
    bedrooms: int = Form(...),
    bathrooms: int = Form(...),
    location: str = Form(...),
    property_type: str = Form(...),
    summary: str = Form(...),
    amenities: list[str] = Form(default_factory=list),
    balconies: Optional[int] = Form(None),
    parking_spots: Optional[int] = Form(None),
    area_sqft: Optional[int] = Form(None),
    facing: Optional[str] = Form(None),
    building_height_type: Optional[str] = Form(None),
    handover_status: Optional[str] = Form(None),
    handover_date: Optional[str] = Form(None),  # "YYYY-MM-DD" or empty
    agent_id: str = Form("agent-demo"),
    brochure: UploadFile = None,
):
    if brochure is None:
        raise HTTPException(status_code=400, detail="brochure PDF file is required")
    if brochure.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="brochure must be a PDF")

    file_bytes = await brochure.read()

    try:
        brochure_text = extract_text_from_pdf(file_bytes)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    embedding = await generate_embedding(summary)

    from supabase import create_client
    supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    storage_path = f"{agent_id}/{uuid.uuid4()}.pdf"
    supabase.storage.from_("brochures").upload(
        storage_path, file_bytes, {"content-type": "application/pdf"}
    )

    handover_date_clean = date_type.fromisoformat(handover_date) if handover_date else None

    pool = get_pool()
    row = await pool.fetchrow(
        """
        insert into properties
            (agent_id, title, brochure_path, brochure_text, summary,
             price, bedrooms, bathrooms, location, property_type, amenities,
             balconies, parking_spots, area_sqft, facing, building_height_type,
             handover_status, handover_date, embedding)
        values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16,
                $17, $18::date, $19)
        returning id, title, summary, price, bedrooms, bathrooms, location, property_type,
                  amenities, balconies, parking_spots, area_sqft, facing,
                  building_height_type, handover_status, handover_date
        """,
        agent_id, title, storage_path, brochure_text, summary,
        price, bedrooms, bathrooms, location, property_type, amenities,
        balconies, parking_spots, area_sqft, facing, building_height_type,
        handover_status, handover_date_clean, embedding,
    )

    return _row_to_out(row)


@router.patch("/{property_id}", response_model=PropertyOut)
async def update_property(property_id: str, updates: PropertyUpdate):
    fields = {k: v for k, v in updates.model_dump().items() if v is not None}
    if "handover_date" in fields and fields["handover_date"]:
        fields["handover_date"] = date_type.fromisoformat(fields["handover_date"])
    if not fields:
        raise HTTPException(status_code=400, detail="No fields provided to update")

    pool = get_pool()
    set_clauses = []
    params = []
    for key, value in fields.items():
        params.append(value)
        cast = "::date" if key == "handover_date" else ""
        set_clauses.append(f"{key} = ${len(params)}{cast}")
    params.append(property_id)

    sql = f"""
        update properties
        set {', '.join(set_clauses)}
        where id = ${len(params)}::uuid
        returning id, title, summary, price, bedrooms, bathrooms, location, property_type,
                  amenities, balconies, parking_spots, area_sqft, facing,
                  building_height_type, handover_status, handover_date
    """
    row = await pool.fetchrow(sql, *params)
    if row is None:
        raise HTTPException(status_code=404, detail="Property not found")

    return _row_to_out(row)