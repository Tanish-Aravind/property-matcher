import { useState } from "react";
import { searchProperties, rerankResults } from "./api";
import { AMENITIES_LIST } from "./amenities";
import { labelFor } from "./constants";

function SearchScreen() {
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState({
    min_price: "", max_price: "", bedrooms: "", location: "", property_type: "", amenities: [],
  });
  const [candidates, setCandidates] = useState([]);
  const [reasons, setReasons] = useState({});
  const [rankedOrder, setRankedOrder] = useState(null);
  const [status, setStatus] = useState("idle");
  const [errorMsg, setErrorMsg] = useState("");

  function handleFilterChange(e) {
    setFilters({ ...filters, [e.target.name]: e.target.value });
  }

  function toggleAmenityFilter(a) {
    setFilters((prev) => {
      const has = prev.amenities.includes(a);
      return { ...prev, amenities: has ? prev.amenities.filter((x) => x !== a) : [...prev.amenities, a] };
    });
  }

  function buildPayload() {
    const payload = { query };
    if (filters.min_price) payload.min_price = Number(filters.min_price);
    if (filters.max_price) payload.max_price = Number(filters.max_price);
    if (filters.bedrooms) payload.bedrooms = Number(filters.bedrooms);
    if (filters.location) payload.location = filters.location;
    if (filters.property_type) payload.property_type = filters.property_type;
    if (filters.amenities.length > 0) payload.amenities = filters.amenities;
    return payload;
  }

  async function handleSearch(e) {
    e.preventDefault();
    if (!query.trim()) {
      setErrorMsg("Describe what the client is looking for.");
      setStatus("error");
      return;
    }

    setStatus("searching");
    setErrorMsg("");
    setReasons({});
    setRankedOrder(null);

    try {
      const { candidates: results } = await searchProperties(buildPayload());
      setCandidates(results);
      setStatus(results.length > 0 ? "refining" : "done");

      if (results.length > 0) {
        rerankResults(query, results.map((c) => c.id))
          .then(({ results: ranked }) => {
            const reasonMap = {};
            ranked.forEach((r) => { reasonMap[r.id] = r.reason; });
            setReasons(reasonMap);
            setRankedOrder(ranked.map((r) => r.id));
            setStatus("done");
          })
          .catch(() => setStatus("done"));
      }
    } catch (err) {
      setStatus("error");
      setErrorMsg(err.message);
    }
  }

  const displayed = rankedOrder
    ? rankedOrder.map((id) => candidates.find((c) => c.id === id)).filter(Boolean)
    : candidates;

  return (
    <div className="container">
      <h1>Find a match</h1>
      <p className="text-muted">Describe what the client wants, in plain language.</p>

      <form onSubmit={handleSearch} className="card" style={{ display: "grid", gap: "16px", maxWidth: 640 }}>
        <label>
          Client request
          <textarea
            rows={3}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. 3BHK apartment in Koramangala under 1.5cr with a swimming pool"
            required
          />
        </label>

        <details>
          <summary style={{ cursor: "pointer", color: "var(--color-text-muted)", fontSize: "var(--font-size-sm)" }}>
            Optional filters
          </summary>
          <div style={{ display: "grid", gap: "12px", marginTop: "12px" }}>
            <div style={{ display: "flex", gap: "12px" }}>
              <label style={{ flex: 1 }}>
                Min price
                <input name="min_price" type="number" value={filters.min_price} onChange={handleFilterChange} />
              </label>
              <label style={{ flex: 1 }}>
                Max price
                <input name="max_price" type="number" value={filters.max_price} onChange={handleFilterChange} />
              </label>
            </div>
            <label>
              Min bedrooms
              <input name="bedrooms" type="number" value={filters.bedrooms} onChange={handleFilterChange} />
            </label>
            <label>
              Location
              <input name="location" value={filters.location} onChange={handleFilterChange} />
            </label>
            <label>
              Property type
              <select name="property_type" value={filters.property_type} onChange={handleFilterChange}>
                <option value="">Any</option>
                <option value="apartment">Apartment</option>
                <option value="house">House</option>
                <option value="villa">Villa</option>
                <option value="plot">Plot</option>
              </select>
            </label>
            <div>
              <p style={{ marginBottom: "6px", fontSize: "var(--font-size-sm)", color: "var(--color-text-muted)" }}>Amenities</p>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px" }}>
                {AMENITIES_LIST.map((a) => (
                  <label key={a} style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "var(--font-size-sm)" }}>
                    <input type="checkbox" checked={filters.amenities.includes(a)} onChange={() => toggleAmenityFilter(a)} />
                    {a}
                  </label>
                ))}
              </div>
            </div>
          </div>
        </details>

        <button type="submit" disabled={status === "searching"}>
          {status === "searching" ? "Searching..." : "Search"}
        </button>

        {status === "error" && <p style={{ color: "#c62828" }}>{errorMsg}</p>}
      </form>

      {(status === "refining" || status === "done") && (
        <div style={{ marginTop: "24px" }}>
          {status === "refining" && (
            <p className="text-muted" style={{ fontStyle: "italic" }}>Refining matches...</p>
          )}
          {status === "done" && candidates.length === 0 && (
            <p className="text-muted">No properties matched. Try loosening the filters.</p>
          )}

          <div style={{ display: "grid", gap: "12px" }}>
            {displayed.map((c) => (
              <div key={c.id} className="card">
                <h2>{c.title}</h2>
                <p className="text-muted">
                  {c.property_type} · {c.bedrooms} bed · {c.bathrooms} bath · {c.location}
                </p>
                <p className="text-muted">₹{Number(c.price).toLocaleString("en-IN")}</p>
                {c.amenities?.length > 0 && (
                  <p className="text-muted">{c.amenities.join(" · ")}</p>
                )}
                {(c.balconies != null || c.parking_spots != null) && (
                  <p className="text-muted">
                    {c.balconies != null && `${c.balconies} balconies`}
                    {c.balconies != null && c.parking_spots != null && " · "}
                    {c.parking_spots != null && `${c.parking_spots} parking spots`}
                  </p>
                )}
                {c.area_sqft != null && <p className="text-muted">{c.area_sqft} sqft</p>}
                {(c.facing || c.building_height_type) && (
                  <p className="text-muted">
                    {c.facing && labelFor(c.facing)}
                    {c.facing && c.building_height_type && " · "}
                    {c.building_height_type && labelFor(c.building_height_type)}
                  </p>
                )}
                {c.handover_status && (
                  <p className="text-muted">
                    {c.handover_status === "ready_to_move" ? "Ready to move" : `Handover: ${c.handover_date || "TBD"}`}
                  </p>
                )}
                {reasons[c.id] && (
                  <p style={{ color: "var(--color-accent)", fontWeight: 500 }}>{reasons[c.id]}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default SearchScreen;