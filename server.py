import os
import subprocess
from flask import Flask, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

@app.route("/")
def index():
    return jsonify({
        "service": "ETL Presencia Medica",
        "status": "online",
        "endpoints": {
            "/run/sync_all": "Sincronizacion completa (primera vez)",
            "/run/sync_incremental": "Sincronizacion incremental (diaria)",
            "/run/clean": "Limpiar todas las tablas"
        }
    })

def run_script(script_name):
    try:
        # Usar el directorio del script actual como base
        script_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(script_dir, script_name)

        result = subprocess.run(
            ["python3", script_path],
            capture_output=True,
            text=True,
            check=True,
            cwd=script_dir,
            timeout=600  # 10 minutos max
        )
        return jsonify({"status": "ok", "output": result.stdout})
    except subprocess.CalledProcessError as e:
        return jsonify({"status": "error", "error": e.stderr, "stdout": e.stdout}), 500
    except subprocess.TimeoutExpired:
        return jsonify({"status": "error", "error": "Script timeout (10 min)"}), 500
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route("/run/sync_all")
def sync_all():
    return run_script("sync_ALL.py")

@app.route("/run/sync_incremental")
def sync_incremental():
    return run_script("sync_INCREMENTAL.py")

@app.route("/run/clean")
def clean_tables():
    return run_script("clean_all_tables.py")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    from waitress import serve
    serve(app, host="0.0.0.0", port=port)