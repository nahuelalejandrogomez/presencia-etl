import os
import subprocess
from flask import Flask, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

@app.route("/")
def index():
    return jsonify({"service": "ETL Presencia", "status": "online"})

def run_script(script_name):
    try:
        result = subprocess.run(
            ["python3", script_name],
            capture_output=True,
            text=True,
            check=True
        )
        return jsonify({"status": "ok", "output": result.stdout})
    except subprocess.CalledProcessError as e:
        return jsonify({"status": "error", "error": e.stderr}), 500

@app.route("/run/sync_all")
def sync_all():
    return run_script("sync_ALL.py")

@app.route("/run/sync_incremental")
def sync_incremental():
    return run_script("sync_INCREMENTAL.py")

@app.route("/run/clean")
def clean_tables():
    return run_script("clean_all_tables.py")

# ----------------------------------------
#     PRODUCCIÓN (Railway) - Waitress
# ----------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))

    from waitress import serve
    serve(app, host="0.0.0.0", port=port)