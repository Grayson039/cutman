import json
import time
import threading
from flask import Flask, jsonify, request
from flask_cors import CORS
from scrapers.fight_cards import get_upcoming_events, get_event_card
from scrapers.fighters import search_fighters, get_fighter_profile
from parsers.news_feed import fetch_news
from datetime import datetime

app = Flask(__name__)
CORS(app)

_cache = {}
_cache_lock = threading.Lock()


def ttl_cache(seconds):
    """Cache a function's return value in memory for `seconds`, keyed by its args.

    Every route here scrapes an external site (Wikipedia/Tapology/Sherdog) or
    fetches RSS on every call with no persistence layer behind it — without this,
    each page load re-triggers the full scrape chain, which is slow and risks
    getting the server IP rate-limited by the sites it scrapes.

    Every wrapped function returns a (data, error) tuple. A failure (error set,
    no data) is deliberately NOT cached — e.g. a transient block from a scrape
    target should self-heal on the next request, not get locked in for the
    full TTL.
    """
    def decorator(fn):
        def wrapper(*args, **kwargs):
            key = (fn.__name__, args, tuple(sorted(kwargs.items())))
            now = time.time()
            with _cache_lock:
                cached = _cache.get(key)
                if cached and now - cached[0] < seconds:
                    return cached[1]
            result = fn(*args, **kwargs)
            data, error = result
            if not (error and not data):
                with _cache_lock:
                    _cache[key] = (now, result)
            return result
        return wrapper
    return decorator


cached_get_upcoming_events = ttl_cache(600)(get_upcoming_events)     # 10 min
cached_get_event_card = ttl_cache(900)(get_event_card)               # 15 min
cached_fetch_news = ttl_cache(300)(fetch_news)                       # 5 min
cached_search_fighters = ttl_cache(1800)(search_fighters)            # 30 min
cached_get_fighter_profile = ttl_cache(3600)(get_fighter_profile)    # 1 hour


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
    data, errors = cached_get_upcoming_events()
    return app.response_class(
        response=json.dumps(data, default=serialize),
        mimetype='application/json'
    )


@app.route("/api/events/card")
def event_card():
    wiki_url = request.args.get("wiki_url", "").strip()
    if not wiki_url:
        return jsonify({"error": "wiki_url param required"}), 400
    bouts, error = cached_get_event_card(wiki_url)
    if error and not bouts:
        return jsonify({"error": error}), 404
    return app.response_class(
        response=json.dumps({"bouts": bouts}, default=serialize),
        mimetype='application/json'
    )


@app.route("/api/news")
def news():
    data, errors = cached_fetch_news()
    return app.response_class(
        response=json.dumps(data, default=serialize),
        mimetype='application/json'
    )


@app.route("/api/fighters/search")
def fighters_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"error": "q param required"}), 400
    results, error = cached_search_fighters(q)
    if error and not results:
        return jsonify({"error": error}), 404
    return jsonify(results)


@app.route("/api/fighters/<slug>")
def fighter_profile(slug):
    profile, error = cached_get_fighter_profile(slug)
    if error and not profile:
        return jsonify({"error": error}), 404
    return app.response_class(
        response=json.dumps(profile, default=serialize),
        mimetype='application/json'
    )


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    app.run(debug=False, port=port, host="0.0.0.0")
