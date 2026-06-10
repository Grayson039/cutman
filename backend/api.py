from flask import Flask, jsonify, request
from flask_cors import CORS
from scrapers.fight_cards import get_upcoming_events
from scrapers.fighters import search_fighters, get_fighter_profile
from parsers.news_feed import fetch_news
from datetime import datetime

app = Flask(__name__)
CORS(app)


def serialize(obj):
    """Make datetime objects JSON-safe."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/events")
def events():
    data, errors = get_upcoming_events()
    return app.response_class(
        response=__import__('json').dumps(data, default=serialize),
        mimetype='application/json'
    )


@app.route("/api/news")
def news():
    data, errors = fetch_news()
    return app.response_class(
        response=__import__('json').dumps(data, default=serialize),
        mimetype='application/json'
    )


@app.route("/api/fighters/search")
def fighters_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"error": "q param required"}), 400
    results, error = search_fighters(q)
    if error and not results:
        return jsonify({"error": error}), 404
    return jsonify(results)


@app.route("/api/fighters/<slug>")
def fighter_profile(slug):
    profile, error = get_fighter_profile(slug)
    if error and not profile:
        return jsonify({"error": error}), 404
    return app.response_class(
        response=__import__('json').dumps(profile, default=serialize),
        mimetype='application/json'
    )


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    app.run(debug=False, port=port, host="0.0.0.0")
