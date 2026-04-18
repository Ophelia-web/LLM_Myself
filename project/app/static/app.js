const form = document.getElementById("search-form");
const statusEl = document.getElementById("status");
const resultsEl = document.getElementById("results");
const MAPS_KEY_STORAGE = "restaurant-demo.googleMapsApiKey";
const GEMINI_KEY_STORAGE = "restaurant-demo.geminiApiKey";

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderCard(item, index) {
  const d = item.dossier;
  const score = item.score;

  return `
    <article class="card">
      <h3>#${index + 1} ${escapeHtml(d.restaurant_name)}</h3>
      <p><strong>Rating:</strong> ${d.rating} (${d.user_rating_count} reviews)</p>
      <p><strong>Price Level:</strong> ${d.price_level}</p>
      <p><strong>Address:</strong> ${escapeHtml(d.address)}</p>
      <p><strong>Why recommended:</strong> ${escapeHtml(d.why_recommended)}</p>
      <p><strong>Summary:</strong> ${escapeHtml(d.summary)}</p>
      <p><strong>Signature dishes:</strong> ${escapeHtml((d.signature_dishes || []).join(", ") || "N/A")}</p>
      <p><strong>Vibe:</strong> ${escapeHtml(d.vibe)}</p>
      <p><strong>Wait impression:</strong> ${escapeHtml(d.wait_impression)}</p>
      <details>
        <summary>Score breakdown (${score.total})</summary>
        <ul>
          <li>Cuisine match: ${score.cuisine_match}</li>
          <li>Budget match: ${score.budget_match}</li>
          <li>Rating: ${score.rating}</li>
          <li>Review value match: ${score.review_value_match}</li>
          <li>Vibe fit: ${score.vibe_fit}</li>
          <li>Wait penalty: ${score.wait_penalty}</li>
        </ul>
      </details>
    </article>
  `;
}

function restoreStoredKeys() {
  const mapsKeyInput = form.elements.googleMapsApiKey;
  const geminiKeyInput = form.elements.geminiApiKey;

  if (!(mapsKeyInput instanceof HTMLInputElement) || !(geminiKeyInput instanceof HTMLInputElement)) {
    return;
  }

  mapsKeyInput.value = localStorage.getItem(MAPS_KEY_STORAGE) || "";
  geminiKeyInput.value = localStorage.getItem(GEMINI_KEY_STORAGE) || "";
}

function persistKeys(payload) {
  localStorage.setItem(MAPS_KEY_STORAGE, payload.googleMapsApiKey);
  localStorage.setItem(GEMINI_KEY_STORAGE, payload.geminiApiKey);
}

restoreStoredKeys();

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const formData = new FormData(form);
  const payload = {
    googleMapsApiKey: formData.get("googleMapsApiKey")?.toString().trim(),
    geminiApiKey: formData.get("geminiApiKey")?.toString().trim(),
    zipCode: formData.get("zipCode")?.toString().trim(),
    cuisine: formData.get("cuisine")?.toString().trim(),
    partySize: Number(formData.get("partySize")),
    budget: formData.get("budget")?.toString().trim().toLowerCase(),
  };

  if (!payload.googleMapsApiKey || !payload.geminiApiKey) {
    statusEl.textContent = "Please provide both API keys.";
    resultsEl.innerHTML = "";
    return;
  }

  persistKeys(payload);

  statusEl.textContent = "Searching restaurants...";
  resultsEl.innerHTML = "";

  try {
    const response = await fetch("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await response.json();

    if (!response.ok) {
      const message = data?.detail || data?.error?.message || "Request failed";
      throw new Error(message);
    }

    const top = data.top_results || [];
    statusEl.textContent = `Found ${top.length} top recommendations from ${data.total_candidates} candidates.`;

    if (!top.length) {
      resultsEl.innerHTML = `<p class="empty">No recommendations found. Try another ZIP/cuisine.</p>`;
      return;
    }

    resultsEl.innerHTML = top.map((item, i) => renderCard(item, i)).join("");
  } catch (error) {
    statusEl.textContent = "Search failed.";
    resultsEl.innerHTML = `<p class="error">${escapeHtml(error.message || "Unknown error")}</p>`;
  }
});
