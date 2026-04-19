const form = document.getElementById("search-form");
const statusEl = document.getElementById("status");
const resultsEl = document.getElementById("results");
const MAPS_KEY_STORAGE = "restaurant-demo.googleMapsApiKey";
const GEMINI_KEY_STORAGE = "restaurant-demo.geminiApiKey";
let mapsApiKeyForPhoto = "";
const PHOTO_FALLBACK =
  "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?auto=format&fit=crop&w=1200&q=70";

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function buildGooglePhotoUrl(photoReference, mapsApiKey, maxWidth = 720) {
  if (!photoReference || !mapsApiKey) {
    return PHOTO_FALLBACK;
  }
  const params = new URLSearchParams({
    maxwidth: String(maxWidth),
    photoreference: photoReference,
    key: mapsApiKey,
  });
  return `https://maps.googleapis.com/maps/api/place/photo?${params.toString()}`;
}

function reservationBadge(dossier) {
  if (dossier.reservable === true && dossier.reservation_link) {
    return `<a class="badge badge-link" href="${escapeHtml(
      dossier.reservation_link
    )}" target="_blank" rel="noopener noreferrer">Reservable</a>`;
  }
  if (dossier.reservable === false) {
    return `<span class="badge">Not reservable</span>`;
  }
  if (dossier.reservation_link) {
    return `<a class="badge badge-link" href="${escapeHtml(
      dossier.reservation_link
    )}" target="_blank" rel="noopener noreferrer">Reservation info</a>`;
  }
  return `<span class="badge">Reservation unknown</span>`;
}

function renderCard(item, index) {
  const d = item.dossier;
  const score = item.score.total;
  const photos = (d.photos || []).slice(0, 3);
  const photoGallery = photos.length
    ? photos
        .map(
          (photo, photoIndex) => `
            <img
              src="${escapeHtml(
                buildGooglePhotoUrl(photo.photo_reference, mapsApiKeyForPhoto, photoIndex === 0 ? 900 : 560)
              )}"
              alt="${escapeHtml(d.restaurant_name)} photo ${photoIndex + 1}"
              loading="lazy"
              onerror="this.onerror=null;this.src='${PHOTO_FALLBACK}'"
            />
          `
        )
        .join("")
    : `<img src="${PHOTO_FALLBACK}" alt="Food placeholder image" loading="lazy" />`;
  const dishes = escapeHtml((d.signature_dishes || []).join(", ") || "N/A");
  const reservableRow =
    d.reservable === true && d.reservation_link
      ? `<p><strong>Reservation:</strong> Available (<a href="${escapeHtml(
          d.reservation_link
        )}" target="_blank" rel="noopener noreferrer">Book now</a>)</p>`
      : d.reservable === false
        ? `<p><strong>Reservation:</strong> Not available</p>`
        : d.reservation_link
          ? `<p><strong>Reservation:</strong> <a href="${escapeHtml(
              d.reservation_link
            )}" target="_blank" rel="noopener noreferrer">Check details</a></p>`
          : `<p><strong>Reservation:</strong> Unknown</p>`;

  return `
    <article class="card result-card">
      <div class="photo-strip">${photoGallery}</div>
      <div class="card-body">
        <div class="card-top">
          <h3>#${index + 1} ${escapeHtml(d.restaurant_name)}</h3>
          <div class="badge-row">
            <span class="badge">Score ${score}</span>
            ${reservationBadge(d)}
          </div>
        </div>
        <p class="meta-line"><strong>Rating:</strong> ${d.rating} (${d.user_rating_count} reviews)</p>
        <p><strong>Address:</strong> ${escapeHtml(d.address)}</p>
        ${reservableRow}
        <p><strong>Signature dishes:</strong> ${dishes}</p>
        <p><strong>Vibe:</strong> ${escapeHtml(d.vibe || "Unknown")}</p>
        <p><strong>Wait impression:</strong> ${escapeHtml(d.wait_impression || "Unknown")}</p>
        <p class="why"><strong>Why recommended:</strong> ${escapeHtml(d.why_recommended || "Good fit for your request.")}</p>
      </div>
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
    budget: Number(formData.get("budget")),
  };

  if (!payload.googleMapsApiKey || !payload.geminiApiKey) {
    statusEl.textContent = "Please provide both API keys.";
    resultsEl.innerHTML = "";
    return;
  }

  persistKeys(payload);
  mapsApiKeyForPhoto = payload.googleMapsApiKey;

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
    statusEl.textContent = `Found ${top.length} top recommendations`;

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
