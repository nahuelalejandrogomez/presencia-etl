#!/usr/bin/env python3
"""
Script para BORRAR todas las tablas y empezar desde cero
"""
import mysql.connector
from dotenv import load_dotenv
import os

load_dotenv()

TABLES = [
    'Cobradores',
    'Socios', 
    'Liquidaciones',
    'TblObras',
    'TblPlanes',
    'TblFPagos',
    'TblIva',
    'TblZonas',
    'TblPromotores',
    'TbComentariosSocios'
]

def get_mysql_connection():
    return mysql.connector.connect(
        host=os.getenv('COBRANZA_DB_HOST'),
        user=os.getenv('COBRANZA_DB_USER'),
        password=os.getenv('COBRANZA_DB_PASSWORD'),
        database=os.getenv('COBRANZA_DB_NAME'),
        port=int(os.getenv('COBRANZA_DB_PORT', 3306)),
        autocommit=True
    )

print("🗑️  LIMPIANDO TODAS LAS TABLAS...")
print("="*80)

conn = get_mysql_connection()
cursor = conn.cursor()

# Deshabilitar foreign keys
cursor.execute("SET FOREIGN_KEY_CHECKS=0")

for table in TABLES:
    try:
        cursor.execute(f"DROP TABLE IF EXISTS `{table}`")
        print(f"✅ {table} - BORRADA")
    except Exception as e:
        print(f"❌ {table} - Error: {e}")

# Rehabilitar foreign keys
cursor.execute("SET FOREIGN_KEY_CHECKS=1")

conn.close()

print("="*80)
print("✅ TODAS LAS TABLAS BORRADAS")
print("\nAhora puedes ejecutar: venv_project/bin/python sync_ALL.py")
