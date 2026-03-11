# ⚽ Football Agent IA

Mini-agent IA local qui récupère l'actualité football, analyse les sujets chauds et génère des idées de tweets engageants pour ton compte X.

---

## 🏗️ Architecture

```
football-agent/
├── app.py                  ← Backend Flask (API + logique)
├── templates/
│   └── index.html          ← Interface utilisateur
├── static/
│   ├── css/style.css       ← Styles
│   └── js/script.js        ← Logique frontend
├── requirements.txt
├── .env.example
└── README.md
```

**Sources de données :**
- 📰 **News** : Flux RSS (L'Équipe, RMC Sport, Footmercato, Goal FR)
- 📅 **Matchs** : API [football-data.org](https://football-data.org) (gratuite)
- 🤖 **Tweets** : Générés par Claude (Anthropic API)

---

## ⚙️ Installation

### 1. Cloner / télécharger le projet

```bash
cd football-agent
```

### 2. Créer un environnement virtuel Python

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Configurer les clés API

```bash
cp .env.example .env
```

Ouvre `.env` et remplis tes clés :

| Variable | Où l'obtenir | Gratuit ? |
|---|---|---|
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com/settings/keys) | Oui (crédits offerts) |
| `FOOTBALL_DATA_API_KEY` | [football-data.org/client/register](https://www.football-data.org/client/register) | Oui (plan Free) |

> ⚠️ Sans `ANTHROPIC_API_KEY`, les tweets ne seront pas générés.
> ⚠️ Sans `FOOTBALL_DATA_API_KEY`, les matchs ne s'afficheront pas (mais les news fonctionnent quand même).

---

## 🚀 Lancement

```bash
python app.py
```

Ouvre ton navigateur sur : **http://localhost:5000**

---

## 🎯 Fonctionnalités

| Bouton | Action |
|---|---|
| **Actualiser l'actu** | Charge les news RSS + matchs du jour |
| **Proposer des tweets** | Génère 7-10 idées de tweets via Claude |

**Chaque tweet généré inclut :**
- 📝 Le texte du tweet (≤ 240 caractères)
- 🏷️ Une catégorie (transfert / match / polémique / comparaison / tactique)
- 📊 Un score de potentiel d'engagement (1-10)
- 💡 Une explication courte
- 📋 Un bouton "Copier"

---

## 🔧 Dépannage

**Les news ne chargent pas** → Vérifie ta connexion internet. Les flux RSS sont publics.

**Les matchs ne s'affichent pas** → Vérifie ta clé `FOOTBALL_DATA_API_KEY` dans `.env`. Le plan gratuit est suffisant.

**Les tweets ne se génèrent pas** → Vérifie ta clé `ANTHROPIC_API_KEY`. Assure-toi d'avoir des crédits sur ton compte Anthropic.

---

## 📦 Stack technique

- **Backend** : Python 3.10+ / Flask
- **Frontend** : HTML / CSS / JavaScript vanilla
- **IA** : Claude via Anthropic API (claude-opus-4-5)
- **Données foot** : feedparser (RSS) + football-data.org
