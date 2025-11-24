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

@app.route("/run/create_mensajes_table")
def create_mensajes_table():
    """Crear tabla MensajesEnviados para n8n"""
    import mysql.connector
    try:
        conn = mysql.connector.connect(
            host=os.getenv('COBRANZA_DB_HOST'),
            user=os.getenv('COBRANZA_DB_USER'),
            password=os.getenv('COBRANZA_DB_PASSWORD'),
            database=os.getenv('COBRANZA_DB_NAME'),
            port=int(os.getenv('COBRANZA_DB_PORT', 3306))
        )
        cursor = conn.cursor()

        sql = '''
CREATE TABLE IF NOT EXISTS MensajesEnviados (
  id INT AUTO_INCREMENT PRIMARY KEY,
  NUMSOCIO VARCHAR(13) NOT NULL,
  telefono VARCHAR(30),
  mensaje TEXT NOT NULL,
  fecha_envio DATETIME DEFAULT CURRENT_TIMESTAMP,
  estado_envio VARCHAR(20) DEFAULT 'enviado',
  canal VARCHAR(20) DEFAULT 'whatsapp',
  workflow_id VARCHAR(50) DEFAULT 'cobranzas_n8n',
  hash_mensaje VARCHAR(64),
  respuesta_api TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_numsocio (NUMSOCIO),
  INDEX idx_fecha_envio (fecha_envio),
  INDEX idx_hash (hash_mensaje)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''
        cursor.execute(sql)
        conn.commit()

        cursor.execute('DESCRIBE MensajesEnviados')
        columns = [{'field': row[0], 'type': row[1]} for row in cursor.fetchall()]

        cursor.close()
        conn.close()

        return jsonify({"status": "ok", "message": "Tabla MensajesEnviados creada", "columns": columns})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route("/run/add_errormessage_column")
def add_errormessage_column():
    """Agregar columna errormessage a tabla MensajesEnviados"""
    import mysql.connector
    try:
        conn = mysql.connector.connect(
            host=os.getenv('COBRANZA_DB_HOST'),
            user=os.getenv('COBRANZA_DB_USER'),
            password=os.getenv('COBRANZA_DB_PASSWORD'),
            database=os.getenv('COBRANZA_DB_NAME'),
            port=int(os.getenv('COBRANZA_DB_PORT', 3306))
        )
        cursor = conn.cursor()

        # Agregar columna errormessage si no existe
        sql = '''
ALTER TABLE MensajesEnviados
ADD COLUMN IF NOT EXISTS errormessage TEXT NULL AFTER respuesta_api
'''
        cursor.execute(sql)
        conn.commit()

        cursor.execute('DESCRIBE MensajesEnviados')
        columns = [{'field': row[0], 'type': row[1]} for row in cursor.fetchall()]

        cursor.close()
        conn.close()

        return jsonify({"status": "ok", "message": "Columna errormessage agregada", "columns": columns})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route("/run/create_ia_usage_table")
def create_ia_usage_table():
    """Crear tabla IAUsageLogs para tracking de uso de IA"""
    import mysql.connector
    try:
        conn = mysql.connector.connect(
            host=os.getenv('COBRANZA_DB_HOST'),
            user=os.getenv('COBRANZA_DB_USER'),
            password=os.getenv('COBRANZA_DB_PASSWORD'),
            database=os.getenv('COBRANZA_DB_NAME'),
            port=int(os.getenv('COBRANZA_DB_PORT', 3306))
        )
        cursor = conn.cursor()

        sql = '''
CREATE TABLE IF NOT EXISTS IAUsageLogs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  workflow_id VARCHAR(50),
  socio_id VARCHAR(50) NULL,
  telefono VARCHAR(50) NULL,
  input_tokens INT DEFAULT 0,
  output_tokens INT DEFAULT 0,
  total_tokens INT DEFAULT 0,
  latency_ms INT DEFAULT 0,
  model_used VARCHAR(50),
  status VARCHAR(20) DEFAULT 'success',
  errormessage TEXT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_workflow (workflow_id),
  INDEX idx_created (created_at),
  INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
'''
        cursor.execute(sql)
        conn.commit()

        cursor.execute('DESCRIBE IAUsageLogs')
        columns = [{'field': row[0], 'type': row[1]} for row in cursor.fetchall()]

        cursor.close()
        conn.close()

        return jsonify({"status": "ok", "message": "Tabla IAUsageLogs creada", "columns": columns})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route("/debug/file")
def debug_file():
    import os
    mdb_path = "/app/data/Datos1.mdb"
    result = {
        "exists": os.path.exists(mdb_path),
        "path": mdb_path
    }
    if os.path.exists(mdb_path):
        result["size_bytes"] = os.path.getsize(mdb_path)
        result["size_mb"] = round(os.path.getsize(mdb_path) / 1024 / 1024, 2)
        with open(mdb_path, 'rb') as f:
            header = f.read(50)
            result["header_hex"] = header.hex()[:100]
            result["is_lfs_pointer"] = header.startswith(b'version https://git-lfs')
    if os.path.exists("/app/data"):
        result["files_in_data"] = os.listdir("/app/data")
    return jsonify(result)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    from waitress import serve
    serve(app, host="0.0.0.0", port=port)