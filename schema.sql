-- Enable pgvector extension
create extension if not exists vector;

create table if not exists properties (
    id uuid primary key default gen_random_uuid(),
    agent_id uuid not null,
    title text not null,
    brochure_path text not null,           -- Supabase Storage path
    brochure_text text not null,           -- raw extracted PDF text
    summary text not null,                 -- ~150 word LLM summary
    price numeric not null,
    bedrooms int not null,
    bathrooms int not null,
    location text not null,
    property_type text not null,           -- e.g. apartment, house, villa
    embedding vector(768) not null,        -- summary embedding
    created_at timestamptz not null default now()
);

-- Filter indexes (Stage A)
create index if not exists idx_properties_price on properties (price);
create index if not exists idx_properties_bedrooms on properties (bedrooms);
create index if not exists idx_properties_location on properties (location);
create index if not exists idx_properties_type on properties (property_type);

-- Vector similarity index (Stage B)
create index if not exists idx_properties_embedding
    on properties using ivfflat (embedding vector_cosine_ops)
    with (lists = 100);