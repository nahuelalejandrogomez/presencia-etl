import os
import subprocess
from flask import Flask, jsonify
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

@app.route("/")
def index():
    return jsonify({"service": "ETL Presencia", "status": "online"})

@app.route("/run/sync_all")
def run_sync_all():
    try:
        result = subprocess.run(
            ["python3", "sync_ALL.py"],
            capture_output=True,
            text=True,
            check=True
        )
        return jsonify({"status": "ok", "output": result.stdout})
    except subprocess.CalledProcessError as e:
        return jsonify({"status": "error", "error": e.stderr}), 500

@app.route("/run/sync_incremental")
def run_sync_incremental():
    try:
        result = subprocess.run(
            ["python3", "sync_INCREMENTAL.py"],
            capture_output=True,
            text=True,
            check=True
        )
        return jsonify({"status": "ok", "output": result.stdout})
    except subprocess.CalledProcessError as e:
        return jsonify({"status": "error", "error": e.stderr}), 500

@app.route("/run/clean")
def run_clean():
    try:
        result = subprocess.run(
            ["python3", "clean_all_tables.py"],
            capture_output=True,
            text=True,
            check=True
        )
        return jsonify({"status": "ok", "output": result.stdout})
    except subprocess.CalledProcessError as e:
        return jsonify({"status": "error", "error": e.stderr}), 500


# ----------------------------
#   PRODUCCIÓN PARA RAILWAY
# ----------------------------
if __name__ == "__main__":
    # Usa el puerto dinámico que da Railway
    port = int(os.environ.get("PORT", 8000))

    # Usamos "waitress" como servidor de producción
    from waitress import serve
    serve(app, host="0.0.0.0", port=port)