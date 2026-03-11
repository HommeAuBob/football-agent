import os
import re
import random
from datetime import datetime

import feedparser
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template

load_dotenv()

app = Flask(__name__)

FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")

# ─── RSS FEEDS ────────────────────────────────────────────────────────────────
RSS_FEEDS = [
    "https://www.lequipe.fr/rss/actu_rss.xml",
    "https://rmcsport.bfmtv.com/rss/football/",
    "https://www.footmercato.net/feed/",
    "https://www.goal.com/feeds/fr/news",
]


def fetch_football_news(max_items=15):
    """Récupère les news foot depuis les flux RSS."""
    articles = []

    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)

            for entry in feed.entries[:5]:
                title = entry.get("title", "").strip()
                summary = entry.get("summary", entry.get("description", "")).strip()
                summary = re.sub(r"<[^>]+>", "", summary)[:300]
                link = entry.get("link", "")
                published = entry.get("published", "")

                if title:
                    articles.append(
                        {
                            "title": title,
                            "summary": summary,
                            "link": link,
                            "published": published,
                            "source": feed.feed.get("title", url),
                        }
                    )
        except Exception as e:
            print(f"Erreur RSS {url}: {e}")
            continue

    # Dédoublonner par titre
    seen = set()
    unique = []

    for article in articles:
        key = article["title"][:80].lower()
        if key not in seen:
            seen.add(key)
            unique.append(article)

    # Petit filtre anti vieux sujets aberrants / trop datés
    old_keywords = [
        "messi au psg",
        "signature de messi au psg",
        "présentation de messi au psg",
        "lionel messi au psg",
        "messi paris saint germain",
    ]

    filtered = []
    for article in unique:
        title_l = article["title"].lower()
        if any(keyword in title_l for keyword in old_keywords):
            continue
        filtered.append(article)

    return filtered[:max_items]


def fetch_todays_matches():
    """Récupère les matchs du jour via football-data.org."""
    if not FOOTBALL_DATA_API_KEY:
        return [], "Clé API football-data.org manquante dans .env"

    today = datetime.now().strftime("%Y-%m-%d")
    headers = {"X-Auth-Token": FOOTBALL_DATA_API_KEY}
    url = f"https://api.football-data.org/v4/matches?dateFrom={today}&dateTo={today}"

    try:
        resp = requests.get(url, headers=headers, timeout=8)
        resp.raise_for_status()
        data = resp.json()

        matches = []
        for match in data.get("matches", []):
            home = match["homeTeam"]["name"]
            away = match["awayTeam"]["name"]
            competition = match["competition"]["name"]
            status = match["status"]
            score_h = match["score"]["fullTime"]["home"]
            score_a = match["score"]["fullTime"]["away"]
            utc_time = match.get("utcDate", "")[:16].replace("T", " ")

            if status == "FINISHED":
                score_str = f"{score_h} - {score_a}"
            elif status == "IN_PLAY":
                score_str = f"🔴 EN DIRECT {score_h} - {score_a}"
            else:
                score_str = utc_time

            matches.append(
                {
                    "home": home,
                    "away": away,
                    "competition": competition,
                    "status": status,
                    "score": score_str,
                    "time": utc_time,
                }
            )

        return matches, None

    except requests.exceptions.HTTPError as e:
        return [], f"Erreur API matchs: {e}"
    except Exception as e:
        return [], f"Impossible de récupérer les matchs: {e}"


def generate_tweet_ideas(articles, matches):
    """Génère des idées de tweets sans IA payante."""
    topics = []

    for article in articles[:12]:
        title = article.get("title", "").strip()
        if not title:
            continue

        cleaned = re.sub(r"[\"'«»:;!?()\-]+", " ", title)
        words = [word for word in cleaned.split() if len(word) > 2]

        if len(words) >= 2:
            topics.append(" ".join(words[:2]))
        elif words:
            topics.append(words[0])

    for match in matches[:6]:
        topics.append(f"{match['home']} vs {match['away']}")
        topics.append(match["competition"])

    blacklist = {
        "home football",
        "actualités foot",
        "actualites foot",
        "football actualités",
        "football actualites",
        "news foot",
        "football agent",
    }

    clean_topics = []
    for topic in topics:
        if topic.lower() not in blacklist and len(topic.strip()) > 2:
            clean_topics.append(topic.strip())

    topics = clean_topics

    if not topics:
        topics = ["Mbappé", "Haaland", "Real Madrid", "PSG", "Premier League"]

    templates = [
        (
            "comparaison",
            8,
            "Débat éternel entre fans",
            "Soyons honnêtes : {topic} aujourd’hui, c’est vraiment du très haut niveau ou on exagère ?",
        ),
        (
            "polémique",
            9,
            "Sujet qui pousse à répondre",
            "Question sérieuse : on surcote totalement {topic} ou pas du tout ?",
        ),
        (
            "match",
            8,
            "Bon angle avant ou après match",
            "{topic} ce soir : vrai test de niveau ou simple match piège selon vous ?",
        ),
        (
            "transfert",
            7,
            "Très bon pour les fans de clubs",
            "Si votre club pouvait récupérer {topic} demain, vous signez direct ou jamais ?",
        ),
        (
            "comparaison",
            8,
            "Les comparaisons font commenter",
            "{topic} ou un top joueur de son poste : vous choisissez qui honnêtement ?",
        ),
        (
            "polémique",
            9,
            "Prend à contre-pied l’avis dominant",
            "Opinion impopulaire : {topic} reçoit beaucoup trop de hype en ce moment.",
        ),
        (
            "match",
            7,
            "Facile à poster dans l’instant",
            "On en parle ou pas : {topic} peut faire exploser les débats ce soir.",
        ),
        (
            "tactique",
            6,
            "Plus niche mais intéressant",
            "{topic} : vrai problème de niveau ou juste mauvais contexte collectif ?",
        ),
    ]

    tweets = []
    used_texts = set()
    max_attempts = 50
    attempts = 0

    while len(tweets) < 8 and attempts < max_attempts:
        attempts += 1
        topic = random.choice(topics)
        category, score, reason, template = random.choice(templates)
        text = template.format(topic=topic)

        if text in used_texts:
            continue

        used_texts.add(text)
        tweets.append(
            {
                "text": text,
                "category": category,
                "engagement_score": score,
                "reason": reason,
            }
        )

    return tweets, None


# ─── ROUTES ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/news")
def api_news():
    articles = fetch_football_news()
    return jsonify({"articles": articles, "count": len(articles)})


@app.route("/api/matches")
def api_matches():
    matches, error = fetch_todays_matches()
    return jsonify({"matches": matches, "error": error})


@app.route("/api/tweets")
def api_tweets():
    articles = fetch_football_news()
    matches, _ = fetch_todays_matches()
    tweets, error = generate_tweet_ideas(articles, matches)

    if error:
        return jsonify({"error": error, "tweets": []}), 500

    return jsonify({"tweets": tweets})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
