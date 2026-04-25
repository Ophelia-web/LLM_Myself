const form = document.getElementById("search-form");
const statusEl = document.getElementById("status");
const resultsEl = document.getElementById("results");
const advancedSettingsEl = document.getElementById("advanced-settings");
const MAPS_KEY_STORAGE = "restaurant-demo.googleMapsApiKey";
const GEMINI_KEY_STORAGE = "restaurant-demo.geminiApiKey";
const RANK_LABELS = ["Best Overall", "Great Value", "Hidden Gem"];

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
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

function formatNumber(value) {
  const num = Number(value);
  if (!Number.isFinite(num) || num <= 0) {
    return "";
  }
  return num.toLocaleString();
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
    low: "Low",
    medium: "Medium",
    high: "High",
    luxury: "Luxury",
    1: "Low",
    2: "Medium",
    3: "High",
    4: "Luxury",
  };
  return labels[level] || "";
}

function mapLink(dossier) {
  return (
    dossier.maps_link ||
    dossier.reservation_link ||
    `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
      dossier.restaurant_name || ""
    )}`
  );
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

function toListItems(values, fallback = "") {
  const cleaned = Array.isArray(values)
    ? values.map((item) => compactText(item)).filter(Boolean)
    : [];
  if (!cleaned.length) {
    return fallback ? `<li>${escapeHtml(fallback)}</li>` : "";
  }
  return cleaned.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
}

function extractRecommendedDishes(signatureDishes) {
  if (!Array.isArray(signatureDishes)) {
    return [];
  }
  const seen = new Set();
  const cleaned = [];
  for (const dish of signatureDishes) {
    const normalized = compactText(dish);
    if (!normalized) {
      continue;
    }
    const key = normalized.toLowerCase();
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    cleaned.push(normalized);
  }
  return cleaned;
}

function priceLevelText(priceLevel) {
  const level = Number(priceLevel || 0);
  return formatBudgetLabel(level) || "Not available";
}

function renderImageGallery(dossier, title) {
  const displayTitle = title || compactText(dossier.restaurant_name) || "Restaurant pick";
  const images = Array.isArray(dossier.photo_urls)
    ? dossier.photo_urls.filter(Boolean).slice(0, 3)
    : [];

  if (!images.length) {
    const initial = (displayTitle || "R").slice(0, 1).toUpperCase();
    return `
      <div class="image-gallery">
        <div class="gallery-item gallery-placeholder">
          <div class="placeholder-initial">${escapeHtml(initial || "R")}</div>
          <p>No photo available.</p>
        </div>
      </div>
    `;
  }

  return `
    <div class="image-gallery">
      ${images
        .map(
          (url, index) => `
            <img
              class="gallery-item"
              src="${escapeHtml(url)}"
              alt="${escapeHtml(displayTitle)} image ${index + 1}"
              loading="lazy"
            />
          `
        )
        .join("")}
    </div>
  `;
}

function renderReviewEvidenceSection(dossier) {
  const evidence = Array.isArray(dossier.review_evidence)
    ? dossier.review_evidence
    : [];
  if (!evidence.length) {
    return `
      <section class="info-block">
        <h4>Review RAG Evidence</h4>
        <p class="muted">No relevant review evidence was retrieved.</p>
      </section>
    `;
  }

  const evidenceCards = evidence
    .map((item) => {
      const text = compactText(item.text);
      if (!text) {
        return "";
      }
      const byline = [
        compactText(item.author_name),
        compactText(item.relative_time_description),
        item.rating ? `Rating ${item.rating}` : "",
      ]
        .filter(Boolean)
        .join(" • ");
      const matchedTerms = Array.isArray(item.matched_terms)
        ? item.matched_terms.filter(Boolean)
        : [];
      return `
        <article class="evidence-item">
          <p class="evidence-text">"${escapeHtml(text)}"</p>
          ${byline ? `<p class="evidence-meta">${escapeHtml(byline)}</p>` : ""}
          ${
            matchedTerms.length
              ? `<p class="evidence-meta"><strong>Matched terms:</strong> ${escapeHtml(
                  matchedTerms.join(", ")
                )}</p>`
              : ""
          }
        </article>
      `;
    })
    .join("");

  return `
    <section class="info-block">
      <h4>Review RAG Evidence</h4>
      <div class="evidence-list">${evidenceCards || '<p class="muted">No relevant review evidence was retrieved.</p>'}</div>
    </section>
  `;
}

function renderImageAnalysisSection(dossier) {
  const image = dossier.image_analysis || {};
  const visualVibe = compactText(image.visual_vibe);
  const spaceImpression = compactText(image.space_impression);
  const groupSuitability = compactText(image.group_suitability);
  const visualConfidence = compactText(image.visual_confidence);
  const visualCues = Array.isArray(image.food_visual_cues)
    ? image.food_visual_cues.map((cue) => compactText(cue)).filter(Boolean)
    : [];
  const evidenceSummary = compactText(image.image_evidence_summary);
  const hasUsefulImageData =
    Boolean(visualVibe) ||
    Boolean(spaceImpression) ||
    Boolean(groupSuitability) ||
    visualCues.length > 0 ||
    (Boolean(evidenceSummary) &&
      !/unavailable/i.test(evidenceSummary));

  if (!hasUsefulImageData) {
    return `
      <section class="info-block">
        <h4>VLM Image Analysis</h4>
        <p class="muted">Image analysis unavailable.</p>
      </section>
    `;
  }

  return `
    <section class="info-block">
      <h4>VLM Image Analysis</h4>
      ${visualVibe ? `<p><strong>Visual vibe:</strong> ${escapeHtml(visualVibe)}</p>` : ""}
      ${spaceImpression ? `<p><strong>Space impression:</strong> ${escapeHtml(spaceImpression)}</p>` : ""}
      ${groupSuitability ? `<p><strong>Group suitability:</strong> ${escapeHtml(groupSuitability)}</p>` : ""}
      ${visualConfidence ? `<p><strong>Visual confidence:</strong> ${escapeHtml(visualConfidence)}</p>` : ""}
      ${
        visualCues.length
          ? `<p><strong>Food visual cues:</strong></p><ul>${toListItems(
              visualCues
            )}</ul>`
          : ""
      }
      ${evidenceSummary ? `<p class="muted">${escapeHtml(evidenceSummary)}</p>` : ""}
    </section>
  `;
}

function renderScoreBreakdown(item) {
  return `
    <details class="score-breakdown">
      <summary>Score Breakdown</summary>
      <ul>
        <li>Cuisine match: ${escapeHtml(item?.score?.cuisine_match ?? "N/A")}</li>
        <li>Budget match: ${escapeHtml(item?.score?.budget_match ?? "N/A")}</li>
        <li>Rating: ${escapeHtml(item?.score?.rating ?? "N/A")}</li>
        <li>Review value match: ${escapeHtml(item?.score?.review_value_match ?? "N/A")}</li>
        <li>Vibe fit: ${escapeHtml(item?.score?.vibe_fit ?? "N/A")}</li>
        <li>Visual vibe fit: ${escapeHtml(item?.score?.visual_vibe_fit ?? "N/A")}</li>
        <li>Evidence quality: ${escapeHtml(item?.score?.evidence_quality ?? "N/A")}</li>
        <li>Wait penalty: ${escapeHtml(item?.score?.wait_penalty ?? "N/A")}</li>
        <li><strong>Total: ${escapeHtml(item?.score?.total ?? "N/A")}</strong></li>
      </ul>
    </details>
  `;
}

function renderCard(item, index) {
  const dossier = item.dossier || {};
  const score = Math.round(Number(item?.score?.total || 0));
  const shortReason = oneSentence(
    dossier.why_recommended,
    "A reliable choice with strong ratings and useful evidence."
  );
  const recommendedDishes = extractRecommendedDishes(dossier.signature_dishes);
  const address = compactText(dossier.address);
  const title = compactText(dossier.restaurant_name) || "Restaurant pick";
  const label = RANK_LABELS[index] || `#${index + 1} Top Pick`;
  const mapsUrl = mapLink(dossier);
  const summary = compactText(dossier.summary);
  const normalizedSummary =
    summary || "Limited structured summary available from the current review evidence.";
  const priceLabel = priceLevelText(dossier.price_level);
  const rating = Number(dossier.rating);
  const ratingBadge = Number.isFinite(rating) && rating > 0 ? rating.toFixed(1) : "";
  const ratingCount = formatNumber(dossier.user_rating_count);
  const reservationText = resolveReservationText(dossier);

  return `
    <article class="card result-card">
      <div class="result-grid">
        <div class="media-column">
          ${renderImageGallery(dossier, title)}
        </div>
        <div class="card-body">
          <div class="card-top">
            <div>
              <p class="rank-label">${label}</p>
              <h3>${escapeHtml(title)}</h3>
            </div>
            <div class="badge-row">
              ${ratingBadge ? `<span class="badge">★ ${escapeHtml(ratingBadge)}</span>` : ""}
              ${ratingCount ? `<span class="badge">${escapeHtml(ratingCount)} ratings</span>` : ""}
              <span class="badge">Match ${score}</span>
            </div>
          </div>
          <p class="why"><strong>Why recommended:</strong> ${escapeHtml(shortReason)}</p>
          ${
            address
              ? `<p class="meta-line">${escapeHtml(address)}</p>`
              : ""
          }
          <p class="meta-line"><strong>Price level:</strong> ${escapeHtml(priceLabel)}</p>
          <p class="meta-line"><strong>Summary:</strong> ${escapeHtml(normalizedSummary)}</p>
          ${
            recommendedDishes.length
              ? `<p><strong>Recommended dishes:</strong> ${escapeHtml(
                  recommendedDishes.join(", ")
                )}</p>`
              : ""
          }
          ${
            reservationText && !/not available/i.test(reservationText)
              ? `<p><strong>${reservationText}</strong></p>`
              : ""
          }
          <div class="card-links">
            <a class="maps-link" href="${escapeHtml(
              mapsUrl
            )}" target="_blank" rel="noopener noreferrer">View on Maps</a>
          </div>
          ${renderReviewEvidenceSection(dossier)}
          ${renderImageAnalysisSection(dossier)}
          ${renderScoreBreakdown(item)}
        </div>
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
    budget: formData.get("budget")?.toString().trim().toLowerCase(),
  };

  if (!payload.googleMapsApiKey || !payload.geminiApiKey) {
    advancedSettingsEl?.setAttribute("open", "open");
    statusEl.textContent = "Please provide both API keys.";
    resultsEl.innerHTML = "";
    return;
  }

  persistKeys(payload);
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

    resultsEl.innerHTML = top.map((item, i) => renderCard(item, i)).join("");
  } catch (error) {
    statusEl.textContent = "Search failed.";
    resultsEl.innerHTML = `<p class="error">${escapeHtml(error.message || "Unknown error")}</p>`;
  }
});
