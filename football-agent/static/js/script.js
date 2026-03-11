// ── HELPERS ──────────────────────────────────────────────────────
function showLoader(text = "Chargement…") {
  document.getElementById("loader-text").textContent = text;
  document.getElementById("loader").classList.remove("hidden");
}

function hideLoader() {
  document.getElementById("loader").classList.add("hidden");
}

function setLastUpdate() {
  const now = new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
  document.getElementById("last-update").textContent = `Dernière mise à jour : ${now}`;
}

function copyTweet(btn, text) {
  navigator.clipboard.writeText(text).then(() => {
    btn.textContent = "✓ Copié !";
    btn.classList.add("copied");
    setTimeout(() => { btn.textContent = "Copier"; btn.classList.remove("copied"); }, 2000);
  });
}

// ── RENDER MATCHES ────────────────────────────────────────────────
function renderMatches(data) {
  const container = document.getElementById("matches-container");
  const badge = document.getElementById("matches-status");

  if (data.error) {
    badge.textContent = "Indisponible";
    badge.className = "status-badge status-error";
    container.innerHTML = `<div class="error-msg">⚠️ ${data.error}</div>`;
    return;
  }

  if (!data.matches || data.matches.length === 0) {
    badge.textContent = "Aucun match";
    badge.className = "status-badge status-ok";
    container.innerHTML = `<div class="placeholder">Aucun match programmé aujourd'hui</div>`;
    return;
  }

  badge.textContent = `${data.matches.length} match(s)`;
  badge.className = "status-badge status-ok";

  container.innerHTML = data.matches.map(m => {
    const isLive = m.status === "IN_PLAY";
    const isFinished = m.status === "FINISHED";
    const scoreClass = isLive ? "live-score" : isFinished ? "" : "upcoming";
    const cardClass = isLive ? "match-card live" : "match-card";

    return `
      <div class="${cardClass}">
        <div class="match-competition">${m.competition}</div>
        <div class="match-teams">
          <span class="team-name team-home">${m.home}</span>
          <span class="match-score ${scoreClass}">${m.score}</span>
          <span class="team-name team-away">${m.away}</span>
        </div>
      </div>
    `;
  }).join("");
}

// ── RENDER NEWS ───────────────────────────────────────────────────
function renderNews(data) {
  const container = document.getElementById("news-container");
  const countBadge = document.getElementById("news-count");

  if (!data.articles || data.articles.length === 0) {
    container.innerHTML = `<div class="placeholder">Aucune news récupérée. Vérifie ta connexion.</div>`;
    return;
  }

  countBadge.textContent = `${data.articles.length} articles`;

  container.innerHTML = data.articles.map((a, i) => `
    <div class="news-item" style="animation-delay: ${i * 0.04}s">
      <div class="news-source">${a.source}</div>
      <div class="news-title">
        ${a.link ? `<a href="${a.link}" target="_blank" rel="noopener">${a.title}</a>` : a.title}
      </div>
      ${a.summary ? `<div class="news-summary">${a.summary}</div>` : ""}
    </div>
  `).join("");
}

// ── RENDER TWEETS ─────────────────────────────────────────────────
function renderTweets(data) {
  const container = document.getElementById("tweets-container");
  const countBadge = document.getElementById("tweets-count");

  if (!data.tweets || data.tweets.length === 0) {
    container.innerHTML = `<div class="error-msg">⚠️ ${data.error || "Aucun tweet généré."}</div>`;
    return;
  }

  countBadge.textContent = `${data.tweets.length} idées`;

  container.innerHTML = data.tweets.map((t, i) => {
    const score = parseInt(t.engagement_score) || 5;
    const fillWidth = (score / 10) * 100;
    const catKey = (t.category || "match").toLowerCase();
    const catClass = `cat-${catKey.replace(/[éè]/g, "e").replace(/[^a-z]/g, "")}`;

    return `
      <div class="tweet-card" style="animation-delay: ${i * 0.06}s">
        <div class="tweet-meta">
          <span class="tweet-category ${catClass}">${t.category || "match"}</span>
          <div class="engagement-score">
            <div class="score-bar">
              <div class="score-fill" style="width: ${fillWidth}%"></div>
            </div>
            ${score}/10
          </div>
        </div>
        <div class="tweet-text">${t.text}</div>
        ${t.reason ? `<div class="tweet-reason">💡 ${t.reason}</div>` : ""}
        <div class="tweet-actions">
          <button class="btn-copy" onclick="copyTweet(this, \`${t.text.replace(/`/g, "'")}\`)">Copier</button>
        </div>
      </div>
    `;
  }).join("");
}

// ── ACTIONS ───────────────────────────────────────────────────────
async function loadNews() {
  try {
    const res = await fetch("/api/news");
    const data = await res.json();
    renderNews(data);
  } catch (e) {
    document.getElementById("news-container").innerHTML = `<div class="error-msg">⚠️ Erreur réseau: ${e.message}</div>`;
  }
}

async function loadMatches() {
  try {
    const res = await fetch("/api/matches");
    const data = await res.json();
    renderMatches(data);
  } catch (e) {
    document.getElementById("matches-container").innerHTML = `<div class="error-msg">⚠️ Erreur réseau: ${e.message}</div>`;
  }
}

async function loadAll() {
  const btn = document.getElementById("btn-refresh");
  btn.disabled = true;
  showLoader("Récupération de l'actu foot…");

  await Promise.all([loadNews(), loadMatches()]);

  setLastUpdate();
  hideLoader();
  btn.disabled = false;
}

async function loadTweets() {
  const btn = document.getElementById("btn-tweets");
  btn.disabled = true;
  showLoader("Analyse des sujets & génération des tweets…");
  document.getElementById("tweets-container").innerHTML = `<div class="placeholder">Génération en cours…</div>`;

  try {
    const res = await fetch("/api/tweets");
    const data = await res.json();
    renderTweets(data);
  } catch (e) {
    document.getElementById("tweets-container").innerHTML = `<div class="error-msg">⚠️ Erreur: ${e.message}</div>`;
  }

  hideLoader();
  btn.disabled = false;
}

// ── AUTO LOAD ON START ────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", loadAll);
