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

RSS_FEEDS = [
    "https://www.lequipe.fr/rss/actu_rss.xml",
    "https://rmcsport.bfmtv.com/rss/football/",
    "https://www.footmercato.net/feed/",
    "https://www.goal.com/feeds/fr/news",
]

# Entités foot qu'on veut reconnaître en priorité
KNOWN_ENTITIES = [
    "Mbappé", "Haaland", "Bellingham", "Vinicius", "Rodrygo", "Messi", "Cristiano Ronaldo",
    "Neymar", "Salah", "Kane", "Lewandowski", "Yamal", "Pedri", "Musiala", "Griezmann",
    "Dembélé", "Kvaratskhelia", "Saka", "Foden", "De Bruyne",
    "PSG", "Paris", "Real Madrid", "Barça", "Barcelona", "Manchester City", "City",
    "Liverpool", "Arsenal", "Chelsea", "Manchester United", "Bayern", "Dortmund",
    "Juventus", "Milan", "Inter", "Napoli", "Lille", "Marseille", "OM", "Lyon",
    "Monaco", "Lens", "Aston Villa",
    "Ligue des champions", "Champions League", "Ligue Europa", "Europa League",
    "Premier League", "Liga", "Serie A", "Bundesliga", "Ligue 1",
    "Ballon d'Or", "mercato"
]

STOPWORDS = {
    "direct", "live", "suivez", "regardez", "une", "un", "des", "les", "la", "le",
    "du", "de", "d", "au", "aux", "pour", "dans", "après", "apres", "vers", "avec",
    "sur", "son", "sa", "ses", "qui", "est", "pas", "plus", "moins", "important",
    "importante", "retour", "normalité", "normalite", "actualité", "actualites",
    "football", "foot", "home", "news", "match", "aller", "soir", "jour"
}


def clean_text(text):
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("\xa0", " ").strip()
    return text


def fetch_football_news(max_items=15):
    articles = []

    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)

            for entry in feed.entries[:6]:
                title = clean_text(entry.get("title", ""))
                summary = clean_text(entry.get("summary", entry.get("description", "")))[:300]
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

    seen = set()
    unique = []

    for article in articles:
        key = article["title"][:90].lower()
        if key not in seen:
            seen.add(key)
            unique.append(article)

    # petit filtrage d'articles hors sujet / vieux délires remontés
    blocked = [
        "messi au psg",
        "signature de messi au psg",
        "présentation de messi au psg",
        "lionel messi au psg",
    ]

    filtered = []
    for article in unique:
        title_l = article["title"].lower()
        if any(b in title_l for b in blocked):
            continue
        filtered.append(article)

    return filtered[:max_items]


def fetch_todays_matches():
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


def extract_topics_from_articles(articles, matches):
    topics = []

    for article in articles:
        title = article.get("title", "")

        # 1. priorité aux entités connues
        found_entities = []
        for entity in KNOWN_ENTITIES:
            if entity.lower() in title.lower():
                found_entities.append(entity)

        for entity in found_entities:
            if entity not in topics:
                topics.append(entity)

        # 2. détecter des affiches du style PSG-Chelsea
        duel_match = re.findall(r"\b([A-Z][A-Za-zÀ-ÿ]+)\s*[-–]\s*([A-Z][A-Za-zÀ-ÿ]+)\b", title)
        for home, away in duel_match:
            duel = f"{home} vs {away}"
            if duel not in topics:
                topics.append(duel)

        # 3. fallback : mots propres plus propres
        words = re.findall(r"\b[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'-]+\b", title)
        candidates = []
        for w in words:
            wl = w.lower()
            if len(w) < 4:
                continue
            if wl in STOPWORDS:
                continue
            if w.isupper() or w[0].isupper():
                candidates.append(w)

        if len(candidates) >= 2:
            candidate_topic = f"{candidates[0]} {candidates[1]}"
            if candidate_topic not in topics:
                topics.append(candidate_topic)

    for match in matches[:10]:
        duel = f"{match['home']} vs {match['away']}"
        if duel not in topics:
            topics.append(duel)

        if match["competition"] not in topics:
            topics.append(match["competition"])

    clean_topics = []
    seen = set()

    for topic in topics:
        topic = topic.strip()
        topic_l = topic.lower()

        if len(topic) < 3:
            continue
        if topic_l in seen:
            continue
        if topic_l in STOPWORDS:
            continue
        if topic_l.startswith("une "):
            continue
        if topic_l.startswith("direct "):
            continue
        if topic_l.startswith("suivez "):
            continue

        seen.add(topic_l)
        clean_topics.append(topic)

    return clean_topics[:20]


def generate_tweet_ideas(articles, matches):
    topics = extract_topics_from_articles(articles, matches)

    if not topics:
        topics = [
            "Mbappé",
            "Haaland",
            "Real Madrid",
            "PSG",
            "Arsenal",
            "Premier League",
            "Ligue des champions"
        ]

    templates = [
        {
            "category": "polémique",
            "engagement_score": 9,
            "reason": "fait réagir les fans immédiatement",
            "text": "Soyons honnêtes : {topic} est surcoté en ce moment ou les critiques sont injustes ?"
        },
        {
            "category": "comparaison",
            "engagement_score": 8,
            "reason": "les comparaisons créent toujours du débat",
            "text": "{topic} aujourd’hui, vous le mettez vraiment parmi les meilleurs à son poste ou pas encore ?"
        },
        {
            "category": "match",
            "engagement_score": 8,
            "reason": "idéal avant un gros match",
            "text": "{topic} : vrai test ce soir ou simple match qu’une grande équipe doit gagner sans discussion ?"
        },
        {
            "category": "transfert",
            "engagement_score": 8,
            "reason": "les fans projettent leur club",
            "text": "Si votre club peut signer {topic} demain matin, vous dites oui direct ou vous passez votre tour ?"
        },
        {
            "category": "polémique",
            "engagement_score": 9,
            "reason": "opinion tranchée = réponses",
            "text": "Opinion impopulaire : autour de {topic}, il y a beaucoup plus de hype que de vrai niveau. D’accord ou non ?"
        },
        {
            "category": "comparaison",
            "engagement_score": 8,
            "reason": "bon format pour les réponses courtes",
            "text": "Question simple : {topic} ou un top joueur de son poste aujourd’hui, vous choisissez qui ?"
        },
        {
            "category": "tactique",
            "engagement_score": 7,
            "reason": "bon débat pour connaisseurs",
            "text": "{topic} : vrai problème de niveau, de système, ou juste contexte compliqué selon vous ?"
        },
        {
            "category": "match",
            "engagement_score": 8,
            "reason": "fonctionne bien pendant l’actu chaude",
            "text": "On va être honnêtes : {topic} peut faire exploser les débats ce soir ou on en fait trop ?"
        }
    ]

    tweets = []
    used = set()
    attempts = 0

    while len(tweets) < 8 and attempts < 80:
        attempts += 1
        topic = random.choice(topics)
        template = random.choice(templates)

        text = template["text"].format(topic=topic)

        if text in used:
            continue

        used.add(text)
        tweets.append({
            "text": text,
            "category": template["category"],
            "engagement_score": template["engagement_score"],
            "reason": template["reason"]
        })

    return tweets, None


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
