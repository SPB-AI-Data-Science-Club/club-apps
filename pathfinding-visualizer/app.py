"""
Pathfinding Visualizer
All algorithms run client-side; Flask only serves the page.
Kept as a Flask app for parity with the rest of the club's deployments.
"""
from flask import Flask, render_template

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")



@app.after_request
def _no_html_cache(resp):
    # Browsers heuristically cache HTML served without Cache-Control, which
    # leaves visitors on stale pages after a deploy. Force revalidation.
    if resp.mimetype == "text/html":
        resp.headers["Cache-Control"] = "no-cache"
    return resp

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5008)
