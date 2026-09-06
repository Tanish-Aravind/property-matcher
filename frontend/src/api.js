const API_URL = import.meta.env.VITE_API_URL;

export async function extractProperty(file) {
  const formData = new FormData();
  formData.append("brochure", file);
  const res = await fetch(`${API_URL}/properties/extract`, { method: "POST", body: formData });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Extraction failed" }));
    throw new Error(err.detail || "Extraction failed");
  }
  return res.json();
}

export async function confirmProperty(file, fields, agentId = "agent-demo") {
  const formData = new FormData();
  formData.append("brochure", file);
  formData.append("agent_id", agentId);
  Object.entries(fields).forEach(([key, value]) => {
    if (key === "amenities") {
      (value || []).forEach((a) => formData.append("amenities", a));
    } else {
      formData.append(key, value);
    }
  });
  const res = await fetch(`${API_URL}/properties/confirm`, { method: "POST", body: formData });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Save failed" }));
    throw new Error(err.detail || "Save failed");
  }
  return res.json();
}

export async function updateProperty(id, updates) {
  const res = await fetch(`${API_URL}/properties/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Update failed" }));
    throw new Error(err.detail || "Update failed");
  }
  return res.json();
}

export async function searchProperties(criteria) {
  const res = await fetch(`${API_URL}/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(criteria),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Search failed" }));
    throw new Error(err.detail || "Search failed");
  }
  return res.json();
}

export async function rerankResults(query, candidateIds) {
  const res = await fetch(`${API_URL}/search/rerank`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, candidate_ids: candidateIds }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Re-rank failed" }));
    throw new Error(err.detail || "Re-rank failed");
  }
  return res.json();
}