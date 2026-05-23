from flask import Flask, jsonify
from flask_cors import CORS
from scrapers.fight_cards import get_upcoming_events
from parsers.news_feed import fetch_news

app = Flask(__name__)
CORS(app)

@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})

@app.route("/api/events")
def events():
    events, errors = get_upcoming_events() # call the scraper
    return jsonify(events) # send the real data back

@app.route("/api/news")
def news():
    articles, errors = fetch_news()
    return jsonify(articles) 

if __name__ == "__main__":
    app.run(debug=True, port=8000, host='0.0.0.0')