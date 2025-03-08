from flask import Flask, request, jsonify, render_template_string
import json
from collections import Counter
import subprocess

app = Flask(__name__)

with open("gita_verses.json", "r") as f:
    gita = json.load(f)

def query_verse(chap, verse):
    chap_str = str(chap)
    verse_key = f"{chap}.{verse}"
    return next((v for v in gita["chapters"].get(chap_str, []) if v["verse"] == verse_key), None)

def query_text(q):
    q = q.lower().strip()
    matches = []
    keywords = q.split()
    for chap in gita["chapters"].values():
        for v in chap:
            text = (v["english"] + " " + v["hindi"] + " " + v["theme"]).lower()
            score = sum(1 for k in keywords if k in text)
            if score > 0:
                matches.append((v, score))
    return [m[0] for m in sorted(matches, key=lambda x: x[1], reverse=True)][:5]

def recommend_psych(theme):
    all_themes = [v["theme"] for chap in gita["chapters"].values() for v in chap if v["theme"] != theme]
    top_themes = Counter(all_themes).most_common(3)
    return f"Related themes: {', '.join(t for t, _ in top_themes)}"

def get_voice_input():
    try:
        result = subprocess.run(["termux-speech-to-text"], capture_output=True, text=True, timeout=5)
        return result.stdout.strip() if result.returncode == 0 else ""
    except:
        return ""

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Lotus AI - Gita Explorer</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        h1 { color: #333; }
        input { padding: 8px; width: 300px; border: 1px solid #ccc; border-radius: 4px; }
        button { padding: 8px 16px; background: #007BFF; color: white; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { background: #0056b3; }
        .result { background: white; padding: 15px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    </style>
</head>
<body>
    <h1>Lotus AI - Gita Explorer</h1>
    <input type="text" id="query" placeholder="e.g., 2.47, duty, Krishna says about self">
    <button onclick="search()">Search</button>
    <button onclick="voiceSearch()">🎤 Voice</button>
    <div id="results"></div>
    <script>
        function search() {
            let q = document.getElementById("query").value;
            fetchResults(q);
        }
        function voiceSearch() {
            fetch("/voice")
                .then(res => res.json())
                .then(data => {
                    if (data.query) {
                        document.getElementById("query").value = data.query;
                        fetchResults(data.query);
                    } else {
                        document.getElementById("results").innerHTML = "No voice input detected!";
                    }
                });
        }
        function fetchResults(q) {
            fetch(`/search?q=${encodeURIComponent(q)}`)
                .then(res => res.json())
                .then(data => {
                    let html = data.map(v => `
                        <div class="result">
                            <b>Verse ${v.verse}</b><br>
                            <i>Sanskrit:</i> ${v.sanskrit}<br>
                            <i>Hindi:</i> ${v.hindi}<br>
                            <i>English:</i> ${v.english}<br>
                            <i>Theme:</i> ${v.theme}<br>
                            <i>Psych Link:</i> ${v.psych_link}<br>
                            <i>${v.recommend || ''}</i>
                        </div>
                    `).join("");
                    document.getElementById("results").innerHTML = html || "No matches!";
                });
        }
    </script>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    if "." in q and q.split(".")[0].isdigit():
        chap, verse = q.split(".", 1)
        result = query_verse(chap, verse)
        if result:
            result["recommend"] = recommend_psych(result["theme"])
            return jsonify([result])
    else:
        results = query_text(q)
        for r in results:
            r["recommend"] = recommend_psych(r["theme"])
        return jsonify(results)
    return jsonify([])

@app.route("/voice")
def voice():
    query = get_voice_input()
    return jsonify({"query": query})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
