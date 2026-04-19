const form = document.getElementById("search-form");
const statusEl = document.getElementById("status");
const resultsEl = document.getElementById("results");
const advancedSettingsEl = document.getElementById("advanced-settings");
const MAPS_KEY_STORAGE = "restaurant-demo.googleMapsApiKey";
const GEMINI_KEY_STORAGE = "restaurant-demo.geminiApiKey";
let mapsApiKeyForPhoto = "";
const ILLUSTRATED_FALLBACKS = [
  "/static/art/sticker-bowl.svg",
  "/static/art/sticker-toast.svg",
  "/static/art/sticker-coffee.svg",
];
const RANK_LABELS = ["Best Overall", "Great Value", "Hidden Gem"];

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function buildGooglePhotoUrl(photoReference, mapsApiKey, maxWidth = 720) {
  const params = new URLSearchParams({
    maxwidth: String(maxWidth),
    photoreference: photoReference,
    key: mapsApiKey,
  });
  return `https://maps.googleapis.com/maps/api/place/photo?${params.toString()}`;
}

function pickFallbackImage(index) {
  return ILLUSTRATED_FALLBACKS[index % ILLUSTRATED_FALLBACKS.length];
}

function compactText(value) {
  if (!value) {
    return "";
  }
  const cleaned = String(value).replace(/\s+/g, " ").trim();
  if (!cleaned || /^(unknown|n\/a|not available)$/i.test(cleaned)) {
    return "";
  }
  return cleaned;
}

function oneSentence(text, fallback) {
  const compact = compactText(text);
  if (!compact) {
    return fallback;
  }
  const [first] = compact.split(/(?<=[.!?])\s+/);
  return first || fallback;
}

function formatBudgetLabel(level) {
  const labels = {
    1: "Inexpensive",
    2: "Moderate",
    3: "Expensive",
    4: "Very Expensive",
  };
  return labels[level] || "Not available";
}

function mapLink(dossier) {
  return dossier.reservation_link || `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(dossier.restaurant_name || "")}`;
}

function resolveReservationText(dossier) {
  if (dossier.reservable === true) {
    return dossier.reservation_link
      ? `Reservation: Available (<a href="${escapeHtml(
          dossier.reservation_link
        )}" target="_blank" rel="noopener noreferrer">Book now</a>)`
      : "Reservation: Available";
  }
  if (dossier.reservable === false) {
    return "Reservation: Not available";
  }
  if (dossier.reservation_link) {
    return `Reservation: <a href="${escapeHtml(
      dossier.reservation_link
    )}" target="_blank" rel="noopener noreferrer">Check details</a>`;
  }
  return "Reservation: Not available";
}

function safeLine(label, value, icon = "") {
  const text = compactText(value);
  if (!text) {
    return "";
  }
  return `
    <p class="detail-line">
      ${icon ? `<img class="line-icon" src="${icon}" alt="" aria-hidden="true" />` : ""}
      <strong>${label}:</strong> ${escapeHtml(text)}
    </p>
  `;
}

function renderCard(item, index, selectedBudget) {
  const dossier = item.dossier || {};
  const score = Math.round(Number(item?.score?.total || 0));
  const photos = (dossier.photos || []).slice(0, 3);
  const photoGallery = photos.length
    ? photos
        .map(
          (photo, photoIndex) => `
            <img
              src="${escapeHtml(
                buildGooglePhotoUrl(photo.photo_reference, mapsApiKeyForPhoto, photoIndex === 0 ? 900 : 560)
              )}"
              alt="${escapeHtml(dossier.restaurant_name || "Restaurant")} photo ${photoIndex + 1}"
              loading="lazy"
              onerror="this.onerror=null;this.src='${pickFallbackImage(photoIndex)}'"
            />
          `
        )
        .join("")
    : ILLUSTRATED_FALLBACKS.map(
        (imgSrc, imgIndex) =>
          `<img src="${imgSrc}" alt="Illustrated food art ${imgIndex + 1}" loading="lazy" />`
      ).join("");
  const shortReason = oneSentence(
    dossier.why_recommended,
    "A reliable choice with strong ratings and a well-rounded dining experience."
  );
  const dishes = compactText((dossier.signature_dishes || []).join(", "));
  const vibe = compactText(dossier.vibe);
  const wait = compactText(dossier.wait_impression);
  const address = compactText(dossier.address);
  const title = compactText(dossier.restaurant_name) || "Restaurant pick";
  const label = RANK_LABELS[index] || `#${index + 1} Top Pick`;
  const mapsUrl = mapLink(dossier);

  return `
    <article class="card result-card">
      <div class="photo-strip">${photoGallery}</div>
      <div class="card-body">
        <div class="card-top">
          <div>
            <p class="rank-label">${label}</p>
            <h3>${escapeHtml(title)}</h3>
          </div>
          <div class="badge-row">
            <span class="badge"><img src="/static/art/icon-star.svg" alt="" aria-hidden="true" /> ${escapeHtml(
              dossier.rating ?? "N/A"
            )}</span>
            <span class="badge">Match score: ${score} / 100</span>
          </div>
        </div>
        ${
          address
            ? `<p class="meta-line"><img class="line-icon" src="/static/art/icon-map.svg" alt="" aria-hidden="true" /> ${escapeHtml(address)}</p>`
            : ""
        }
        <p class="meta-line"><img class="line-icon" src="/static/art/icon-budget.svg" alt="" aria-hidden="true" /> <strong>Price range:</strong> ${formatBudgetLabel(selectedBudget)}</p>
        <p class="why"><strong>Why you'll like it:</strong> ${escapeHtml(shortReason)}</p>
        ${safeLine("Must-try dishes", dishes, "/static/art/icon-food.svg")}
        ${safeLine("Atmosphere", vibe, "/static/art/icon-map.svg")}
        ${safeLine("Wait time", wait, "/static/art/icon-star.svg")}
        <p><strong>${resolveReservationText(dossier)}</strong></p>
        <a class="maps-link" href="${escapeHtml(
          mapsUrl
        )}" target="_blank" rel="noopener noreferrer">View on Maps</a>
        <details class="why-match">
          <summary>Why this match</summary>
          <ul>
            <li>Cuisine match: ${escapeHtml(item?.score?.cuisine_match ?? "N/A")}</li>
            <li>Budget match: ${escapeHtml(item?.score?.budget_match ?? "N/A")}</li>
            <li>Rating: ${escapeHtml(item?.score?.rating ?? "N/A")}</li>
            <li>Review value match: ${escapeHtml(item?.score?.review_value_match ?? "N/A")}</li>
            <li>Atmosphere fit: ${escapeHtml(item?.score?.vibe_fit ?? "N/A")}</li>
            <li>Wait penalty: ${escapeHtml(item?.score?.wait_penalty ?? "N/A")}</li>
          </ul>
        </details>
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
  if (mapsKeyInput.value || geminiKeyInput.value) {
    advancedSettingsEl?.setAttribute("open", "open");
  }
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
    advancedSettingsEl?.setAttribute("open", "open");
    statusEl.textContent = "Please provide both API keys.";
    resultsEl.innerHTML = "";
    return;
  }

  persistKeys(payload);
  mapsApiKeyForPhoto = payload.googleMapsApiKey;

  statusEl.textContent = "Finding the best spots for you...";
  resultsEl.innerHTML = `
    <article class="card skeleton-card" aria-hidden="true"></article>
    <article class="card skeleton-card" aria-hidden="true"></article>
    <article class="card skeleton-card" aria-hidden="true"></article>
  `;

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
      resultsEl.innerHTML = `
        <p class="empty">
          No great matches found.<br />
          Try changing your filters.
        </p>
      `;
      return;
    }

    resultsEl.innerHTML = top.map((item, i) => renderCard(item, i, payload.budget)).join("");
  } catch (error) {
    statusEl.textContent = "Search failed.";
    resultsEl.innerHTML = `<p class="error">${escapeHtml(error.message || "Unknown error")}</p>`;
  }
});
