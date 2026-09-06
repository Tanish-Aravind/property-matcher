import { useState } from "react";
import { extractProperty, confirmProperty } from "./api";
import { AMENITIES_LIST } from "./amenities";
import { FACING_OPTIONS, BUILDING_HEIGHT_OPTIONS, HANDOVER_STATUS_OPTIONS, labelFor } from "./constants";
const emptyReview = {
  title: "", price: "", bedrooms: "", bathrooms: "", location: "", property_type: "apartment",
  summary: "", amenities: [], balconies: "", parking_spots: "",
  area_sqft: "", facing: "", building_height_type: "", handover_status: "", handover_date: "",
};

function UploadScreen() {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | extracting | review | saving | saved | error
  const [errorMsg, setErrorMsg] = useState("");
  const [review, setReview] = useState(emptyReview);
  const [saved, setSaved] = useState(null);

  function handleFileChange(e) {
    setFile(e.target.files[0] || null);
    setStatus("idle");
    setErrorMsg("");
  }

  async function handleExtract(e) {
    e.preventDefault();
    if (!file) {
      setErrorMsg("Please attach a brochure PDF.");
      setStatus("error");
      return;
    }
    setStatus("extracting");
    setErrorMsg("");
    try {
      const fields = await extractProperty(file);
      setReview({
        ...fields,
        amenities: fields.amenities || [],
        balconies: fields.balconies ?? "",
        parking_spots: fields.parking_spots ?? "",
        area_sqft: fields.area_sqft ?? "",
        facing: fields.facing ?? "",
        building_height_type: fields.building_height_type ?? "",
        handover_status: fields.handover_status ?? "",
        handover_date: fields.handover_date ?? "",
      });
      setStatus("review");
    } catch (err) {
      setStatus("error");
      setErrorMsg(err.message);
    }
  }

  function handleReviewChange(e) {
    setReview({ ...review, [e.target.name]: e.target.value });
  }

  function toggleAmenity(amenity) {
    setReview((prev) => {
      const has = prev.amenities.includes(amenity);
      return {
        ...prev,
        amenities: has ? prev.amenities.filter((a) => a !== amenity) : [...prev.amenities, amenity],
      };
    });
  }

  async function handleConfirm() {
    setStatus("saving");
    setErrorMsg("");
    try {
      const fields = {
        title: review.title,
        price: Number(review.price),
        bedrooms: Number(review.bedrooms),
        bathrooms: Number(review.bathrooms),
        location: review.location,
        property_type: review.property_type,
        summary: review.summary,
        amenities: review.amenities,
      };
      if (review.balconies !== "") fields.balconies = Number(review.balconies);
      if (review.parking_spots !== "") fields.parking_spots = Number(review.parking_spots);
      if (review.area_sqft !== "") fields.area_sqft = Number(review.area_sqft);
      if (review.facing) fields.facing = review.facing;
      if (review.building_height_type) fields.building_height_type = review.building_height_type;
      if (review.handover_status) fields.handover_status = review.handover_status;
      if (review.handover_status === "under_construction" && review.handover_date) {
        fields.handover_date = review.handover_date;
      }
      const property = await confirmProperty(file, fields);
      setSaved(property);
      setStatus("saved");
    } catch (err) {
      setStatus("review");
      setErrorMsg(err.message);
    }
  }

  function startOver() {
    setFile(null);
    setReview(emptyReview);
    setSaved(null);
    setStatus("idle");
    setErrorMsg("");
  }

  return (
    <div className="container">
      <h1>Upload property</h1>
      <p className="text-muted">Attach a brochure PDF, review the extracted details, then confirm to save.</p>

      {(status === "idle" || status === "extracting" || status === "error") && (
        <form onSubmit={handleExtract} className="card" style={{ display: "grid", gap: "16px", maxWidth: 480 }}>
          <label>
            Brochure (PDF)
            <input type="file" accept="application/pdf" onChange={handleFileChange} required />
          </label>
          <button type="submit" disabled={status === "extracting" || !file}>
            {status === "extracting" ? "Extracting details..." : "Extract details"}
          </button>
          {status === "error" && <p style={{ color: "#c62828" }}>{errorMsg}</p>}
        </form>
      )}

      {(status === "review" || status === "saving") && (
        <div className="card" style={{ maxWidth: 480, display: "grid", gap: "12px" }}>
          <p className="text-muted">Check these details before saving — the AI extracted them from the brochure.</p>

          <label>
            Title
            <input name="title" value={review.title} onChange={handleReviewChange} />
          </label>
          <label>
            Price (INR)
            <input name="price" type="number" value={review.price} onChange={handleReviewChange} />
          </label>
          <div style={{ display: "flex", gap: "12px" }}>
            <label style={{ flex: 1 }}>
              Bedrooms
              <input name="bedrooms" type="number" value={review.bedrooms} onChange={handleReviewChange} />
            </label>
            <label style={{ flex: 1 }}>
              Bathrooms
              <input name="bathrooms" type="number" value={review.bathrooms} onChange={handleReviewChange} />
            </label>
          </div>
          <label>
            Location
            <input name="location" value={review.location} onChange={handleReviewChange} />
          </label>
          <label>
            Property type
            <select name="property_type" value={review.property_type} onChange={handleReviewChange}>
              <option value="apartment">Apartment</option>
              <option value="house">House</option>
              <option value="villa">Villa</option>
              <option value="plot">Plot</option>
            </select>
          </label>

          <div style={{ display: "flex", gap: "12px" }}>
            <label style={{ flex: 1 }}>
              Balconies
              <input name="balconies" type="number" value={review.balconies} onChange={handleReviewChange} />
            </label>
            <label style={{ flex: 1 }}>
              Parking spots
              <input name="parking_spots" type="number" value={review.parking_spots} onChange={handleReviewChange} />
            </label>
          </div>

          <label>
            Unit size (sqft)
            <input name="area_sqft" type="number" value={review.area_sqft} onChange={handleReviewChange} />
          </label>

          <div style={{ display: "flex", gap: "12px" }}>
            <label style={{ flex: 1 }}>
              Facing
              <select name="facing" value={review.facing} onChange={handleReviewChange}>
                <option value="">Not specified</option>
                {FACING_OPTIONS.map((f) => <option key={f} value={f}>{labelFor(f)}</option>)}
              </select>
            </label>
            <label style={{ flex: 1 }}>
              Building type
              <select name="building_height_type" value={review.building_height_type} onChange={handleReviewChange}>
                <option value="">Not specified</option>
                {BUILDING_HEIGHT_OPTIONS.map((b) => <option key={b} value={b}>{labelFor(b)}</option>)}
              </select>
            </label>
          </div>

          <div style={{ display: "flex", gap: "12px" }}>
            <label style={{ flex: 1 }}>
              Handover status
              <select name="handover_status" value={review.handover_status} onChange={handleReviewChange}>
                <option value="">Not specified</option>
                {HANDOVER_STATUS_OPTIONS.map((h) => <option key={h} value={h}>{labelFor(h)}</option>)}
              </select>
            </label>
            {review.handover_status === "under_construction" && (
              <label style={{ flex: 1 }}>
                Expected handover
                <input name="handover_date" type="date" value={review.handover_date} onChange={handleReviewChange} />
              </label>
            )}
          </div>

          <div>
            <p style={{ marginBottom: "6px" }}>Amenities</p>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px" }}>
              {AMENITIES_LIST.map((a) => (
                <label key={a} style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "var(--font-size-sm)" }}>
                  <input type="checkbox" checked={review.amenities.includes(a)} onChange={() => toggleAmenity(a)} />
                  {a}
                </label>
              ))}
            </div>
          </div>

          <label>
            Summary
            <textarea rows={5} name="summary" value={review.summary} onChange={handleReviewChange} />
          </label>

          <div style={{ display: "flex", gap: "12px" }}>
            <button onClick={handleConfirm} disabled={status === "saving"}>
              {status === "saving" ? "Saving..." : "Confirm & save"}
            </button>
            <button
              onClick={startOver}
              disabled={status === "saving"}
              style={{ background: "transparent", color: "var(--color-text-muted)" }}
            >
              Start over
            </button>
          </div>
          {errorMsg && <p style={{ color: "#c62828" }}>{errorMsg}</p>}
        </div>
      )}

      {status === "saved" && saved && (
        <div className="card" style={{ maxWidth: 480 }}>
          <h2>{saved.title}</h2>
          <p className="text-muted">
            {saved.property_type} · {saved.bedrooms} bed · {saved.bathrooms} bath · {saved.location}
          </p>
          <p className="text-muted">₹{Number(saved.price).toLocaleString("en-IN")}</p>
          {saved.amenities?.length > 0 && (
            <p className="text-muted">{saved.amenities.join(" · ")}</p>
          )}
          <p>{saved.summary}</p>
          <button onClick={startOver} style={{ marginTop: "12px" }}>Upload another</button>
        </div>
      )}
    </div>
  );
}

export default UploadScreen;