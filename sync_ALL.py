#!/usr/bin/env python3
"""Sincronización COMPLETA de todas las tablas"""

from dotenv import load_dotenv
load_dotenv()

import os
import subprocess
import csv
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
# Se aplican en read_access_table() después de mdb-export
TABLE_FILTERS = {
    'Socios': {
        'BAJA': '1'      # Excluir socios dados de baja (BAJA=1)
        # 'COMSOCIO': 'CU'  # Deshabilitado - cargamos todos los socios activos
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

def infer_column_type(col_name):
    """
    Inferir tipo de columna por nombre basado en convenciones de Access.
    
    Orden de prioridad:
    1. Fechas (FEC, FECHA, DATE, ALT con COB)
    2. Montos/importes específicos (IMP, MONTO, PRECIO, ABO/COB específicos)
    3. IDs, códigos y números enteros (NUM, COD, ID, POS, PRO, ZON, ULT, CANT)
    4. Texto por defecto
    """
    col_upper = col_name.upper()
    
    # 1. Fechas: FEC, FECHA, DATE, y casos específicos como ALTCOB (fecha de alta)
    if ('FEC' in col_upper or 'FECHA' in col_upper or 'DATE' in col_upper or
        col_upper in ['ALTCOB', 'ALTSOCIO', 'BAJAFECHA', 'PERLIQUIDANRO', 'F1CSOCIO', 'FBUSCAHR']):
        return 'DATETIME NULL'
    
    # 2. Campos DECIMAL (montos, importes, precios, comisiones)
    # Específicos para evitar falsos positivos:
    elif (col_upper.startswith('IMP') or col_upper.startswith('MONTO') or 
          col_upper.startswith('PRECIO') or col_upper.startswith('TOTAL') or
          col_upper.endswith('IMP') or col_upper.endswith('MONTO') or
          col_upper.endswith('PRECIO') or 'IMPORTE' in col_upper or 
          'COMISION' in col_upper or
          col_upper in ['ABOLIQUIDA', 'COMCOB', 'IMPSOCIO', 'SUBFACTURA']):
        return 'DECIMAL(15,4) NULL'
    
    # 3. Campos INT (códigos, números de ID, posiciones, provincias, zonas, etc)
    # PERO: NUMSOCIO, NUMPROMOTOR, NUMFACTURA, CUPLIQUIDA son Text en Access
    elif (((col_upper.startswith('NUM') or col_upper.startswith('COD') or 
            col_upper.startswith('ID') or col_upper.startswith('CANT') or
            col_upper.startswith('POS') or col_upper.startswith('PRO') or
            col_upper.startswith('ZON') or col_upper.startswith('ULT') or
            col_upper.endswith('COB') or col_upper.endswith('SOCIO') or
            col_upper.endswith('ZONA') or col_upper.endswith('LIQUIDA')) and
           # Excepciones que son TEXT en Access:
           col_upper not in ['NUMSOCIO', 'NUMPROMOTOR', 'NUMFACTURA', 'CUPLIQUIDA', 'SOCLIQUIDA',
                           'OBSCOB', 'OBISOCIO', 'NOMCOB', 'DOMCOB', 'LOCCOB', 'TELCOB', 'CELCOB',
                           'IVACOB', 'CUICOB', 'NOMSOCIO', 'FANSOCIO', 'DOMSOCIO', 'LOCSOCIO',
                           'PROSOCIO', 'TELSOCIO', 'IVASOCIO', 'CUISOCIO', 'COMSOCIO', 'DESZONA',
                           'ESTLIQUIDA', 'PERLIQUIDA', 'OBSLIQUIDA', 'PAGLIQUIDA', 'COMLIQUIDA']) or
          # Campos específicos que sabemos que son INT:
          col_upper in ['BAJA', 'POSCOB', 'PROCOB', 'ULTCOB', 'ZONCOB', 'COBSOCIO',
                       'PLASOCIO', 'ZONSOCIO', 'POSSOCIO', 'SUBSOCIO', 'ZONLIQUIDA', 'COBLIQUIDA']):
        return 'INT NULL'
    
    # 4. Por defecto: VARCHAR
    else:
        return 'VARCHAR(255) NULL'

def convert_date_value(value):
    """Convertir fechas de formato Access a formato MySQL"""
    if not value or value == '':
        return None
    
    try:
        # Access exporta fechas como: "01/27/22 00:00:00"
        # Intentar varios formatos
        for fmt in ['%m/%d/%y %H:%M:%S', '%m/%d/%Y %H:%M:%S', '%Y-%m-%d %H:%M:%S']:
            try:
                dt = datetime.strptime(value, fmt)
                # Convertir a formato MySQL: YYYY-MM-DD HH:MM:SS
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

def sync_table(table_name, conn, cursor):
    """Sincronizar una tabla completa"""
    print(f"\n{'='*80}")
    print(f"TABLA: {table_name}")
    print('='*80)
    
    # 1. Leer desde Access
    print(f"1. Leyendo {table_name} desde Access...")
    try:
        rows = read_access_table(table_name)
        if not rows:
            print(f"   ⚠️  Tabla vacía, saltando...")
            return
        print(f"   ✅ {len(rows):,} registros leídos")
    except Exception as e:
        print(f"   ❌ Error leyendo: {e}")
        return
    
    # 2. Analizar columnas
    print(f"2. Analizando esquema...")
    all_cols = get_all_columns(rows)
    print(f"   ✅ {len(all_cols)} columnas encontradas")
    
    # 3. Crear tabla
    print(f"3. Creando/recreando tabla...")
    try:
        cursor.execute(f"DROP TABLE IF EXISTS `{table_name}`")
        
        col_defs = ["`id` INT AUTO_INCREMENT PRIMARY KEY"]
        for col in all_cols:
            col_defs.append(f"`{col}` {infer_column_type(col)}")
        
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
    
    # 4. Insertar datos
    print(f"4. Insertando {len(rows):,} registros...")
    cursor.execute("SET FOREIGN_KEY_CHECKS=0")
    cursor.execute("SET UNIQUE_CHECKS=0")
    
    batch_size = 1000
    inserted = 0
    
    # Agregar row_hash a las columnas
    placeholders = ', '.join(['%s'] * (len(all_cols) + 1))  # +1 para row_hash
    col_names = ', '.join([f'`{col}`' for col in all_cols]) + ', `row_hash`'
    insert_sql = f"INSERT INTO `{table_name}` ({col_names}) VALUES ({placeholders})"
    
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        
        # Mostrar progreso cada 10,000 registros
        if i > 0 and i % 10000 == 0:
            print(f"   ... {inserted:,} / {len(rows):,}")
        
        values = []
        for row in batch:
            # Calcular hash
            row_hash = calculate_row_hash(row, all_cols)
            # Convertir fechas y agregar valores
            row_values = []
            for col in all_cols:
                val = row.get(col) if row.get(col) else None
                # Convertir fechas si el nombre de columna contiene FEC, FECHA, DATE o es campo DateTime específico
                col_upper = col.upper()
                if val and ('FEC' in col_upper or 'FECHA' in col_upper or 'DATE' in col_upper or 
                           col_upper in ['PERLIQUIDANRO', 'F1CSOCIO', 'FBUSCAHR', 'ALTCOB', 'ALTSOCIO', 'BAJAFECHA']):
                    val = convert_date_value(val)
                row_values.append(val)
            values.append(tuple(row_values) + (row_hash,))
        
        try:
            cursor.executemany(insert_sql, values)
            inserted += len(batch)
        except Exception as e:
            # Intentar uno por uno si falla el batch
            for row in batch:
                try:
                    row_hash = calculate_row_hash(row, all_cols)
                    row_values = []
                    for col in all_cols:
                        val = row.get(col) if row.get(col) else None
                        col_upper = col.upper()
                        if val and ('FEC' in col_upper or 'FECHA' in col_upper or 'DATE' in col_upper or 
                                   col_upper in ['PERLIQUIDANRO', 'F1CSOCIO', 'FBUSCAHR', 'ALTCOB', 'ALTSOCIO', 'BAJAFECHA']):
                            val = convert_date_value(val)
                        row_values.append(val)
                    cursor.execute(insert_sql, tuple(row_values) + (row_hash,))
                    inserted += 1
                except:
                    pass
    
    cursor.execute("SET FOREIGN_KEY_CHECKS=1")
    cursor.execute("SET UNIQUE_CHECKS=1")
    
    # 5. Verificar
    cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
    final_count = cursor.fetchone()[0]
    
    print(f"   ✅ COMPLETADO: {final_count:,} registros en MySQL")

# MAIN
print("="*80)
print("SINCRONIZACIÓN COMPLETA DE TODAS LAS TABLAS")
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
