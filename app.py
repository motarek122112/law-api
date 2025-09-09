import os, json, requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# ---- اقرأ إعدادات Elasticsearch من Environment variables ----
ES_URL   = os.getenv("ES_URL")        # مثال: https://...:32162
ES_INDEX = os.getenv("ES_INDEX")      # egypt_law_text  (أو الاسم القديم اللي هترجعله)
ES_USER  = os.getenv("ES_USER")
ES_PASS  = os.getenv("ES_PASS")

TIMEOUT = 20

def get_es_hit(article_num:int, filename:str):
    headers = {"Content-Type":"application/json"}
    body = {
        "_source": ["article_label","content","law","filename","article_num"],
        "size": 1,
        "query": {
            "bool": {
                "must": [{"term": {"article_num": article_num}}],
                "filter": [{"term": {"filename": filename}}]
            }
        }
    }
    r = requests.post(f"{ES_URL}/{ES_INDEX}/_search",
                      headers=headers, auth=(ES_USER, ES_PASS),
                      data=json.dumps(body), timeout=TIMEOUT, verify=True)
    r.raise_for_status()
    hits = r.json().get("hits", {}).get("hits", [])
    return hits[0]["_source"] if hits else None

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status":"ok"})

@app.route("/", methods=["POST"])
def handler():
    data = request.get_json(force=True, silent=True) or {}
    article = int(data.get("article", 0))
    filename = data.get("file", "")
    if not (article and filename):
        return jsonify({"error":"send JSON: {\"article\": <int>, \"file\": \"<filename>\"}"}), 400

    try:
        hit = get_es_hit(article, filename)
    except Exception as e:
        return jsonify({"found": False, "message": f"ES error: {str(e)}"}), 500

    if not hit:
        return jsonify({"found": False, "message":"No match in Elasticsearch"}), 404

    return jsonify({
        "found": True,
        "article": article,
        "article_label": hit.get("article_label",""),
        "filename": hit.get("filename",""),
        "law": hit.get("law",""),
        "quote": hit.get("content","").strip()
    })

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
