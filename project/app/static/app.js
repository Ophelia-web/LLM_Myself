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
    low: "Low ($)",
    medium: "Medium ($$)",
    high: "High ($$$)",
    luxury: "Luxury ($$$$)",
    1: "Inexpensive",
    2: "Moderate",
    3: "Expensive",
    4: "Very Expensive",
  };
  return labels[level] || "Not available";
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

function toListItems(values, fallback = "Not enough evidence yet.") {
  const cleaned = Array.isArray(values)
    ? values.map((item) => compactText(item)).filter(Boolean)
    : [];
  if (!cleaned.length) {
    return `<li>${escapeHtml(fallback)}</li>`;
  }
  return cleaned.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
}

function priceLevelText(priceLevel) {
  const level = Number(priceLevel || 0);
  if (!level || level < 1 || level > 4) {
    return "Not available";
  }
  return "$".repeat(level);
}

function renderHeroMedia(dossier) {
  const title = compactText(dossier.restaurant_name) || "Restaurant pick";
  const heroUrl = dossier.photo_urls?.[0];
  if (heroUrl) {
    return `
      <div class="card-hero">
        <img
          class="hero-image"
          src="${escapeHtml(heroUrl)}"
          alt="${escapeHtml(title)} hero photo"
          loading="lazy"
        />
        <div class="hero-gradient"></div>
      </div>
    `;
  }

  const initial = title.slice(0, 1).toUpperCase();
  return `
    <div class="card-hero card-hero-placeholder">
      <div class="placeholder-initial">${escapeHtml(initial || "R")}</div>
      <p>No photo available.</p>
    </div>
  `;
}

function renderThumbnails(dossier) {
  const thumbnails = (dossier.photo_urls || []).slice(1, 3);
  if (!thumbnails.length) {
    return "";
  }
  return `
    <div class="thumb-row">
      ${thumbnails
        .map(
          (url, index) => `
            <img
              src="${escapeHtml(url)}"
              alt="${escapeHtml(dossier.restaurant_name || "Restaurant")} thumbnail ${
                index + 2
              }"
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
      const text = compactText(item.text) || "No snippet text.";
      const byline = [
        compactText(item.author_name) || "Anonymous",
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
          <p class="evidence-meta">${escapeHtml(byline || "Google Places review")}</p>
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
      <div class="evidence-list">${evidenceCards}</div>
    </section>
  `;
}

function renderImageAnalysisSection(dossier) {
  const image = dossier.image_analysis || {};
  return `
    <section class="info-block">
      <h4>VLM Image Analysis</h4>
      <p><strong>Visual vibe:</strong> ${escapeHtml(compactText(image.visual_vibe) || "unknown")}</p>
      <p><strong>Space impression:</strong> ${escapeHtml(
        compactText(image.space_impression) || "unknown"
      )}</p>
      <p><strong>Group suitability:</strong> ${escapeHtml(
        compactText(image.group_suitability) || "unknown"
      )}</p>
      <p><strong>Visual confidence:</strong> ${escapeHtml(
        compactText(image.visual_confidence) || "low"
      )}</p>
      <p><strong>Food visual cues:</strong></p>
      <ul>${toListItems(image.food_visual_cues, "Unknown")}</ul>
      <p class="muted">${escapeHtml(
        compactText(image.image_evidence_summary) || "Image analysis was unavailable."
      )}</p>
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
  const dishes = compactText((dossier.signature_dishes || []).join(", "));
  const address = compactText(dossier.address);
  const title = compactText(dossier.restaurant_name) || "Restaurant pick";
  const label = RANK_LABELS[index] || `#${index + 1} Top Pick`;
  const mapsUrl = mapLink(dossier);
  const summary = compactText(
    [dossier.service, dossier.value, dossier.vibe].filter(Boolean).join(" | ")
  );

  return `
    <article class="card result-card">
      ${renderHeroMedia(dossier)}
      ${renderThumbnails(dossier)}
      <div class="card-body">
        <div class="card-top">
          <div>
            <p class="rank-label">${label}</p>
            <h3>${escapeHtml(title)}</h3>
          </div>
          <div class="badge-row">
            <span class="badge">Rating ${escapeHtml(dossier.rating ?? "N/A")}</span>
            <span class="badge">${escapeHtml(dossier.user_rating_count ?? 0)} ratings</span>
            <span class="badge">Match score: ${score} / 100</span>
          </div>
        </div>
        ${
          address
            ? `<p class="meta-line">${escapeHtml(address)}</p>`
            : ""
        }
        <p class="meta-line"><strong>Price level:</strong> ${escapeHtml(
          priceLevelText(dossier.price_level)
        )} (${escapeHtml(formatBudgetLabel(dossier.price_level))})</p>
        <p class="meta-line"><strong>Summary:</strong> ${escapeHtml(summary || "Unknown")}</p>
        <p class="why"><strong>Why recommended:</strong> ${escapeHtml(shortReason)}</p>
        <p><strong>Signature dishes:</strong> ${escapeHtml(dishes || "Unknown")}</p>
        <p><strong>${resolveReservationText(dossier)}</strong></p>
        <a class="maps-link" href="${escapeHtml(
          mapsUrl
        )}" target="_blank" rel="noopener noreferrer">View on Maps</a>
        ${renderReviewEvidenceSection(dossier)}
        ${renderImageAnalysisSection(dossier)}
        ${renderScoreBreakdown(item)}
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
