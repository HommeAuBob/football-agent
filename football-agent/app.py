import os
import feedparser
import requests
from flask import Flask, jsonify, render_template
from datetime import datetime
from dotenv import load_dotenv
import anthropic

load_dotenv()

app = Flask(__name__)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
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
                # Nettoyer le HTML basique
                import re
                summary = re.sub(r"<[^>]+>", "", summary)[:300]
                link = entry.get("link", "")
                published = entry.get("published", "")
                if title:
                    articles.append({
                        "title": title,
                        "summary": summary,
                        "link": link,
                        "published": published,
                        "source": feed.feed.get("title", url)
                    })
        except Exception as e:
            print(f"Erreur RSS {url}: {e}")
            continue

    # Dédoublonner par titre
    seen = set()
    unique = []
    for a in articles:
        key = a["title"][:60].lower()
        if key not in seen:
            seen.add(key)
            unique.append(a)

    return unique[:max_items]


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
        for m in data.get("matches", []):
            home = m["homeTeam"]["name"]
            away = m["awayTeam"]["name"]
            competition = m["competition"]["name"]
            status = m["status"]
            score_h = m["score"]["fullTime"]["home"]
            score_a = m["score"]["fullTime"]["away"]
            utc_time = m.get("utcDate", "")[:16].replace("T", " ")

            score_str = ""
            if status == "FINISHED":
                score_str = f"{score_h} - {score_a}"
            elif status == "IN_PLAY":
                score_str = f"🔴 EN DIRECT {score_h} - {score_a}"
            else:
                score_str = utc_time

            matches.append({
                "home": home,
                "away": away,
                "competition": competition,
                "status": status,
                "score": score_str,
                "time": utc_time
            })
        return matches, None
    except requests.exceptions.HTTPError as e:
        return [], f"Erreur API matchs: {e}"
    except Exception as e:
        return [], f"Impossible de récupérer les matchs: {e}"


def extract_key_topics(articles):
    """Extrait les sujets clés depuis les titres des articles."""
    titles = [a["title"] for a in articles]
    return "\n".join(f"- {t}" for t in titles)


def generate_tweet_ideas(articles, matches):
    """Envoie les sujets à Claude pour générer des idées de tweets."""
    if not ANTHROPIC_API_KEY:
        return None, "Clé ANTHROPIC_API_KEY manquante dans .env"

    news_summary = extract_key_topics(articles)

    match_lines = ""
    if matches:
        match_lines = "\n".join(
            f"- {m['home']} vs {m['away']} ({m['competition']}) — {m['score']}"
            for m in matches[:10]
        )
    else:
        match_lines = "Aucun match récupéré."

    prompt = f"""Tu es un expert en content marketing football sur X (Twitter).
Voici l'actualité foot du moment :

=== NEWS ===
{news_summary}

=== MATCHS DU JOUR ===
{match_lines}

Ta mission : générer entre 7 et 10 idées de tweets football, optimisées pour l'engagement maximum sur X.

Règles strictes :
- Chaque tweet fait MAX 240 caractères
- Orientés débat, provocation intelligente, ou opinion forte
- Variés : transferts, résultats, polémiques, comparaisons légendes
- Pas de hashtags génériques
- Ton direct, authentique, comme un vrai fan passionné
- Commence directement par les tweets, sans introduction

Pour chaque tweet, retourne ce format JSON :
{{
  "tweets": [
    {{
      "text": "contenu du tweet",
      "category": "transfert | match | polémique | comparaison | tactique",
      "engagement_score": 1-10,
      "reason": "pourquoi ça va buzzer (max 15 mots)"
    }}
  ]
}}

Réponds UNIQUEMENT avec le JSON, rien d'autre."""

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        import json
        raw = message.content[0].text.strip()
        # Nettoyer les backticks JSON si présents
        raw = raw.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)
        return data.get("tweets", []), None
    except Exception as e:
        return None, f"Erreur génération tweets: {e}"


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


@app.route('/api/tweets')
def generate_tweets():
    news = get_football_news()

    tweets = []

    templates = [
        "Soyons honnêtes : {topic} est-il vraiment au niveau attendu cette saison ?",
        "Question sérieuse : est-ce que {topic} est surcoté actuellement ?",
        "Débat du jour : {topic} ou un autre joueur à ce poste ?",
        "Si votre club pouvait signer {topic} demain, vous prenez ?",
        "On en parle assez de {topic} cette saison ou pas ?",
        "Opinion impopulaire : {topic} n'est peut-être pas aussi fort que tout le monde le dit.",
        "Soyons honnêtes : {topic} est-il top 5 mondial à son poste ?",
        "Votre avis : {topic} ballon d'or un jour ou impossible ?"
    ]

    import random

    topics = []

    for article in news[:10]:
        title = article.get("title", "")
        words = title.split()
        if len(words) > 2:
            topics.append(words[0] + " " + words[1])

    if not topics:
        topics = ["Mbappé", "Haaland", "Real Madrid", "PSG", "Premier League"]

    for i in range(8):
        topic = random.choice(topics)
        template = random.choice(templates)
        tweets.append(template.format(topic=topic))

    return jsonify({
        "tweets": tweets
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
