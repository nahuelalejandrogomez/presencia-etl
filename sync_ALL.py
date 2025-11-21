#!/usr/bin/env python3
"""Sincronización COMPLETA de todas las tablas - Usando esquema real de Access"""

from dotenv import load_dotenv
load_dotenv()

import os
import subprocess
import csv
import re
from io import StringIO
import mysql.connector
from collections import OrderedDict
import hashlib
from datetime import datetime

ACCESS_DB = os.getenv('COBRANZA_ACCESS_PATH', '/Users/nahuel/Documents/Desarrollos/P_M_Cobranza/BBDD/Datos1.mdb')

# Lista de tablas principales a sincronizar
TABLES = [
    'Cobradores',
    'Socios',  # ⚠️ FILTRADO: Solo BAJA<>1 (activos)
    'Liquidaciones',
    'TblObras',
    'TblPlanes',
    'TblFPagos',
    'TblIva',
    'TblZonas',
    'TblPromotores',
    'TbComentariosSocios'
]

# 🔥 FILTROS: Solo se excluyen socios dados de baja
TABLE_FILTERS = {
    'Socios': {
        'BAJA': '1'      # Excluir socios dados de baja (BAJA=1)
    }
}

def get_mysql_connection():
    """Conectar a MySQL"""
    config = {
        'host': os.getenv('COBRANZA_DB_HOST'),
        'user': os.getenv('COBRANZA_DB_USER'),
        'password': os.getenv('COBRANZA_DB_PASSWORD'),
        'database': os.getenv('COBRANZA_DB_NAME'),
        'port': int(os.getenv('COBRANZA_DB_PORT', 3306)),
        'autocommit': True
    }
    return mysql.connector.connect(**config)

def get_access_schema(table_name):
    """Obtener esquema real de tabla desde Access usando mdb-schema"""
    result = subprocess.run(
        ['mdb-schema', ACCESS_DB, 'mysql'],
        capture_output=True,
        text=True,
        check=True
    )

    # Buscar la definición de la tabla específica
    schema_text = result.stdout

    # Regex para encontrar CREATE TABLE específico
    pattern = rf'CREATE TABLE `{table_name}`\s*\(\s*(.*?)\);'
    match = re.search(pattern, schema_text, re.DOTALL | re.IGNORECASE)

    if not match:
        return None

    columns_text = match.group(1)
    columns = {}

    # Parsear cada línea de columna
    for line in columns_text.split('\n'):
        line = line.strip().rstrip(',')
        if not line or line.startswith('--'):
            continue

        # Extraer nombre y tipo: `COLUMNA` tipo
        col_match = re.match(r'`(\w+)`\s+(.+)', line)
        if col_match:
            col_name = col_match.group(1)
            col_type_raw = col_match.group(2).strip()

            # Convertir tipos de Access/mdb-schema a MySQL compatibles
            col_type = convert_access_type_to_mysql(col_type_raw)
            columns[col_name] = col_type

    return columns

def convert_access_type_to_mysql(access_type):
    """Convertir tipo de mdb-schema a tipo MySQL válido"""
    access_type_lower = access_type.lower()

    # Remover NOT NULL por ahora, lo agregamos después si es necesario
    is_not_null = 'not null' in access_type_lower
    access_type_clean = access_type_lower.replace('not null', '').strip()

    # Mapeo de tipos
    if 'auto_increment' in access_type_clean:
        return 'INT'  # Ignoramos auto_increment porque usamos nuestro ID
    elif access_type_clean.startswith('varchar'):
        # Extraer tamaño
        match = re.search(r'varchar\s*\((\d+)\)', access_type_clean)
        size = match.group(1) if match else '255'
        return f'VARCHAR({size})'
    elif access_type_clean == 'text':
        return 'TEXT'
    elif access_type_clean in ['smallint', 'int', 'integer']:
        return 'INT'
    elif access_type_clean in ['double', 'float']:
        return 'DOUBLE'
    elif access_type_clean == 'boolean':
        return 'TINYINT(1)'
    elif access_type_clean in ['date', 'datetime']:
        return 'DATETIME'
    else:
        return 'VARCHAR(255)'  # Default

def read_access_table(table_name):
    """Leer tabla desde Access aplicando filtros si existen"""
    result = subprocess.run(
        ['mdb-export', ACCESS_DB, table_name],
        capture_output=True,
        text=True,
        check=True
    )
    reader = csv.DictReader(StringIO(result.stdout))
    rows = list(reader)

    # Aplicar filtros en Python si existen para esta tabla
    if table_name in TABLE_FILTERS:
        filters = TABLE_FILTERS[table_name]

        if table_name == 'Socios' and isinstance(filters, dict):
            # Filtro 1: BAJA<>1 (excluir dados de baja)
            if 'BAJA' in filters:
                exclude_value = filters['BAJA']
                rows = [row for row in rows if row.get('BAJA') != exclude_value]

            # Filtro 2: COMSOCIO='CU' (solo socios con cupones)
            if 'COMSOCIO' in filters:
                required_value = filters['COMSOCIO']
                rows = [row for row in rows if row.get('COMSOCIO') == required_value]

    return rows

def get_all_columns(rows):
    """Obtener todas las columnas únicas de todos los registros"""
    all_cols = OrderedDict()
    for row in rows:
        for col in row.keys():
            if col not in all_cols:
                all_cols[col] = True
    return list(all_cols.keys())

def convert_date_value(value):
    """Convertir fechas de formato Access a formato MySQL"""
    if not value or value == '':
        return None

    try:
        # Access exporta fechas como: "01/27/22 00:00:00"
        for fmt in ['%m/%d/%y %H:%M:%S', '%m/%d/%Y %H:%M:%S', '%Y-%m-%d %H:%M:%S', '%m/%d/%y', '%m/%d/%Y']:
            try:
                dt = datetime.strptime(value, fmt)
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                continue
        return None
    except:
        return None

def calculate_row_hash(row, columns):
    """Calcular hash SHA-256 de una fila"""
    values = []
    for col in sorted(columns):
        val = row.get(col, '')
        values.append(str(val) if val else 'NULL')
    content = '|'.join(values)
    return hashlib.sha256(content.encode()).hexdigest()

def is_date_column(col_type):
    """Verificar si el tipo es fecha/datetime"""
    return col_type.upper() in ['DATE', 'DATETIME']

def sync_table(table_name, conn, cursor):
    """Sincronizar una tabla completa usando esquema real de Access"""
    print(f"\n{'='*80}")
    print(f"TABLA: {table_name}")
    print('='*80)

    # 1. Obtener esquema real de Access
    print(f"1. Obteniendo esquema de Access...")
    schema = get_access_schema(table_name)
    if not schema:
        print(f"   ⚠️  No se pudo obtener esquema, usando inferencia...")
        schema = None
    else:
        print(f"   ✅ Esquema obtenido: {len(schema)} columnas")

    # 2. Leer datos desde Access
    print(f"2. Leyendo datos desde Access...")
    try:
        rows = read_access_table(table_name)
        if not rows:
            print(f"   ⚠️  Tabla vacía, saltando...")
            return
        print(f"   ✅ {len(rows):,} registros leídos")
    except Exception as e:
        print(f"   ❌ Error leyendo: {e}")
        return

    # 3. Determinar columnas
    all_cols = get_all_columns(rows)
    print(f"   ✅ {len(all_cols)} columnas en datos")

    # 4. Crear tabla
    print(f"3. Creando/recreando tabla en MySQL...")
    try:
        cursor.execute(f"DROP TABLE IF EXISTS `{table_name}`")

        col_defs = ["`id` INT AUTO_INCREMENT PRIMARY KEY"]
        for col in all_cols:
            if schema and col in schema:
                col_type = schema[col]
            else:
                col_type = 'VARCHAR(255)'  # Default si no está en esquema
            col_defs.append(f"`{col}` {col_type} NULL")

        col_defs.append("`row_hash` VARCHAR(64) NULL")
        col_defs.append("`created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        col_defs.append("`updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")

        create_sql = f"""
        CREATE TABLE `{table_name}` (
            {', '.join(col_defs)}
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
        cursor.execute(create_sql)
        print(f"   ✅ Tabla creada")
    except Exception as e:
        print(f"   ❌ Error creando tabla: {e}")
        return

    # 5. Insertar datos
    print(f"4. Insertando {len(rows):,} registros...")
    cursor.execute("SET FOREIGN_KEY_CHECKS=0")
    cursor.execute("SET UNIQUE_CHECKS=0")

    batch_size = 1000
    inserted = 0

    placeholders = ', '.join(['%s'] * (len(all_cols) + 1))
    col_names = ', '.join([f'`{col}`' for col in all_cols]) + ', `row_hash`'
    insert_sql = f"INSERT INTO `{table_name}` ({col_names}) VALUES ({placeholders})"

    # Determinar columnas de fecha basándonos en el esquema
    date_columns = set()
    if schema:
        for col, col_type in schema.items():
            if is_date_column(col_type):
                date_columns.add(col)

    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]

        if i > 0 and i % 10000 == 0:
            print(f"   ... {inserted:,} / {len(rows):,}")

        values = []
        for row in batch:
            row_hash = calculate_row_hash(row, all_cols)
            row_values = []
            for col in all_cols:
                val = row.get(col) if row.get(col) else None
                # Convertir fechas si la columna es de tipo fecha
                if val and col in date_columns:
                    val = convert_date_value(val)
                row_values.append(val)
            values.append(tuple(row_values) + (row_hash,))

        try:
            cursor.executemany(insert_sql, values)
            inserted += len(batch)
        except Exception as e:
            print(f"   ⚠️ Error en batch: {e}")
            # Intentar uno por uno si falla el batch
            for row in batch:
                try:
                    row_hash = calculate_row_hash(row, all_cols)
                    row_values = []
                    for col in all_cols:
                        val = row.get(col) if row.get(col) else None
                        if val and col in date_columns:
                            val = convert_date_value(val)
                        row_values.append(val)
                    cursor.execute(insert_sql, tuple(row_values) + (row_hash,))
                    inserted += 1
                except Exception as row_err:
                    if inserted == 0:
                        print(f"   ⚠️ Error en registro: {row_err}")
                        print(f"      Columnas: {all_cols}")
                        print(f"      Valores: {row_values[:5]}...")

    cursor.execute("SET FOREIGN_KEY_CHECKS=1")
    cursor.execute("SET UNIQUE_CHECKS=1")

    # 6. Verificar
    cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
    final_count = cursor.fetchone()[0]

    print(f"   ✅ COMPLETADO: {final_count:,} registros en MySQL")

# MAIN
print("="*80)
print("SINCRONIZACIÓN COMPLETA - USANDO ESQUEMA REAL DE ACCESS")
print("="*80)

conn = get_mysql_connection()
cursor = conn.cursor()

results = {}
for table in TABLES:
    try:
        sync_table(table, conn, cursor)
        cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
        count = cursor.fetchone()[0]
        results[table] = count
    except Exception as e:
        print(f"\n❌ Error en {table}: {e}")
        results[table] = 0

cursor.close()
conn.close()

# RESUMEN FINAL
print("\n" + "="*80)
print("RESUMEN FINAL")
print("="*80)
total = 0
for table, count in results.items():
    print(f"{table:30s}: {count:>10,} registros")
    total += count
print("-"*80)
print(f"{'TOTAL':30s}: {total:>10,} registros")
print("="*80)
