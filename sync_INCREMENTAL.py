#!/usr/bin/env python3
"""Sincronización INCREMENTAL basada en hashes"""

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

# Tablas principales
TABLES = [
    'Cobradores',      # FILTRADO: NUMCOB=30
    'Socios',          # FILTRADO: COBSOCIO=30
    'Liquidaciones',   # FILTRADO: COBLIQUIDA=30 AND BAJA<>1
    'TblObras',        # SIN FILTRO (todas)
    'TblPlanes',       # SIN FILTRO (todas)
    'TblFPagos',       # SIN FILTRO (todas)
    'TblIva',          # SIN FILTRO (todas)
    'TblZonas',        # SIN FILTRO (todas)
    'TblPromotores',   # SIN FILTRO (todas)
    'TbComentariosSocios'  # FILTRADO: Indirecto via socios del cobrador 30
]

# 🔥 FILTROS: Solo cobrador 30 y relacionados
TABLE_FILTERS = {
    'Cobradores': {
        'NUMCOB': '30'          # Solo cobrador 30
    },
    'Socios': {
        'COBSOCIO': '30'        # Solo socios del cobrador 30
    },
    'Liquidaciones': {
        'COBLIQUIDA': '30',     # Solo liquidaciones del cobrador 30
        'BAJA': '1'             # Excluir liquidaciones dadas de baja (BAJA=1)
    }
}

# ⚠️ TABLAS CON FULL REFRESH: No tienen clave única confiable
# Se hace DROP/CREATE en cada sync (como sync_ALL.py)
FULL_REFRESH_TABLES = ['Socios']

def get_mysql_connection():
    config = {
        'host': os.getenv('COBRANZA_DB_HOST'),
        'user': os.getenv('COBRANZA_DB_USER'),
        'password': os.getenv('COBRANZA_DB_PASSWORD'),
        'database': os.getenv('COBRANZA_DB_NAME'),
        'port': int(os.getenv('COBRANZA_DB_PORT', 3306)),
        'autocommit': True
    }
    return mysql.connector.connect(**config)

def read_access_table(table_name, socios_numsocio_list=None):
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

        # Filtro genérico: Para cada clave en filters
        for field, value in filters.items():
            if field == 'BAJA':
                # BAJA: excluir si BAJA=value (normalmente '1')
                rows = [row for row in rows if row.get(field) != value]
            else:
                # Otros campos: incluir solo si campo=value
                rows = [row for row in rows if row.get(field) == value]

    # Filtro especial para TbComentariosSocios: solo comentarios de socios filtrados
    if table_name == 'TbComentariosSocios' and socios_numsocio_list:
        rows = [row for row in rows if row.get('NUMSOCIO') in socios_numsocio_list]

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
    """Calcula hash de una fila para detectar cambios"""
    values = []
    for col in sorted(columns):
        val = row.get(col, '')
        values.append(str(val) if val else 'NULL')
    content = '|'.join(values)
    return hashlib.sha256(content.encode()).hexdigest()

def get_unique_key_column(table_name, all_cols):
    """
    Determina LA columna o COLUMNAS únicas de cada tabla según Access.
    Retorna una lista de columnas (puede ser 1 o más).
    
    REGLA: Cada tabla tiene un campo ID único que se usa para matching.
    - Socios: NUMSOCIO + NOMSOCIO (combinación - muchos tienen NUMSOCIO=0)
    - Cobradores: NUMCOB (✅ verificado único)
    - Liquidaciones: CUPLIQUIDA (✅ verificado único)
    - TblObras: NUNOSOCIAL (✅ verificado único)
    - TblPlanes: NUMPLAN (✅ verificado único)
    - Otras: primera columna por defecto
    """
    key_map = {
        'Cobradores': ['NUMCOB'],           # ✅ Único verificado
        'Socios': ['NUMSOCIO', 'NOMSOCIO'], # ⚠️ Combinación (NUMSOCIO tiene duplicados en 0)
        'Liquidaciones': ['CUPLIQUIDA'],    # ✅ Único verificado (confirmado por usuario)
        'TblObras': ['NUNOSOCIAL'],         # ✅ Único verificado
        'TblPlanes': ['NUMPLAN'],           # ✅ Único verificado
        'TblFPagos': ['NUMFPAGO'],          # Por verificar
        'TblIva': ['CATIVA'],               # Por verificar
        'TblZonas': ['NUMZONA'],            # Por verificar
        'TblPromotores': ['NUMPROMOTOR'],   # Por verificar
        'TbComentariosSocios': ['IdComment']  # Por verificar
    }
    
    key_cols = key_map.get(table_name, [all_cols[0]])  # Default: primera columna como lista
    # Verificar que todas existen en all_cols
    valid_cols = [col for col in key_cols if col in all_cols]
    if not valid_cols:
        valid_cols = [all_cols[0]]
    return valid_cols

def normalize_key_value(value):
    """Normaliza valores para comparación (maneja decimales, espacios, etc.)"""
    if value is None:
        return ''
    s = str(value).strip()
    # Si parece un número decimal, convertir a float y luego a string sin ceros innecesarios
    try:
        f = float(s)
        # Si es entero, devolver sin decimales
        if f == int(f):
            return str(int(f))
        return str(f)
    except:
        return s

def get_existing_records(cursor, table_name, unique_key_cols):
    """Carga registros existentes: {unique_key_value: (id, row_hash)}"""
    records = {}
    skipped_nulls = 0
    duplicates_found = 0
    try:
        # Construir SELECT con todas las columnas clave
        cols_select = ', '.join([f'`{col}`' for col in unique_key_cols])
        cursor.execute(f"SELECT id, {cols_select}, row_hash FROM `{table_name}`")
        
        for row in cursor.fetchall():
            row_id = row[0]
            # row_hash es siempre la última columna
            row_hash_idx = len(unique_key_cols) + 1  # id + columnas_clave + row_hash
            row_hash = row[row_hash_idx] if row[row_hash_idx] else ''
            
            # Si hay múltiples columnas clave, concatenar con |
            if len(unique_key_cols) == 1:
                key_value = normalize_key_value(row[1])
            else:
                # Concatenar todas las columnas clave
                key_parts = [normalize_key_value(row[i+1]) for i in range(len(unique_key_cols))]
                key_value = '|'.join(key_parts)
            
            # DEBUG: Detectar colisiones y valores vacíos
            if key_value in records:
                duplicates_found += 1
                if table_name == 'Socios' and duplicates_found <= 5:
                    print(f"   ⚠️  Clave duplicada detectada: '{key_value}' (IDs: {records[key_value][0]} y {row_id})")
            
            if '|' in key_value and (key_value.startswith('|') or key_value.endswith('|') or '||' in key_value):
                skipped_nulls += 1
                if table_name == 'Socios' and skipped_nulls <= 5:
                    print(f"   ⚠️  Registro con NULL en clave: '{key_value}' (ID: {row_id})")
            
            records[key_value] = (row_id, row_hash)
        
        if table_name == 'Socios' and (duplicates_found > 0 or skipped_nulls > 0):
            print(f"   ⚠️  Total duplicados: {duplicates_found}, Total con NULLs: {skipped_nulls}")
    
    except Exception as e:
        pass  # Tabla no existe o está vacía
    return records

def sync_table_full_refresh(table_name, conn, cursor, rows):
    """
    FULL REFRESH: DROP + CREATE + INSERT (como sync_ALL.py)
    Se usa para tablas sin clave única confiable (ej: Socios)
    """
    print(f"\n{'='*80}")
    print(f"TABLA: {table_name} [FULL REFRESH]")
    print('='*80)
    
    print(f"1. Registros a sincronizar: {len(rows):,}")
    
    # 2. Analizar columnas
    print(f"2. Analizando esquema...")
    all_cols = get_all_columns(rows)
    print(f"   ✅ {len(all_cols)} columnas encontradas")
    
    # 3. Crear tabla
    print(f"3. Recreando tabla...")
    try:
        cursor.execute(f"DROP TABLE IF EXISTS `{table_name}`")
        
        col_defs = ["`id` INT AUTO_INCREMENT PRIMARY KEY"]
        for col in all_cols:
            col_type = infer_column_type(col)
            col_defs.append(f"`{col}` {col_type}")
        col_defs.append("`row_hash` VARCHAR(64) NULL")
        col_defs.append("`created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        col_defs.append("`updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
        
        create_sql = f"CREATE TABLE `{table_name}` ({', '.join(col_defs)}) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
        cursor.execute(create_sql)
        print(f"   ✅ Tabla recreada")
    except Exception as e:
        print(f"   ❌ Error creando tabla: {e}")
        return
    
    # 4. Insertar datos
    print(f"4. Insertando {len(rows):,} registros...")
    try:
        batch_size = 1000
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i+batch_size]
            
            if i > 0 and i % 10000 == 0:
                print(f"   ... {i:,} / {len(rows):,}")
            
            # Preparar datos con hash
            insert_data = []
            for row in batch:
                values = []
                for col in all_cols:
                    val = row.get(col, None)
                    val = val if val != '' else None
                    # Convertir fechas
                    col_upper = col.upper()
                    if val and ('FEC' in col_upper or 'FECHA' in col_upper or 'DATE' in col_upper or 
                               col_upper in ['PERLIQUIDANRO', 'F1CSOCIO', 'FBUSCAHR', 'ALTCOB', 'ALTSOCIO', 'BAJAFECHA']):
                        val = convert_date_value(val)
                    values.append(val)
                
                # Calcular hash
                row_hash = calculate_row_hash(row, all_cols)
                values.append(row_hash)
                insert_data.append(tuple(values))
            
            # INSERT
            placeholders = ', '.join(['%s'] * (len(all_cols) + 1))  # +1 por row_hash
            cols = ', '.join([f'`{col}`' for col in all_cols] + ['`row_hash`'])
            insert_sql = f"INSERT INTO `{table_name}` ({cols}) VALUES ({placeholders})"
            cursor.executemany(insert_sql, insert_data)
        
        print(f"   ✅ COMPLETADO: {len(rows):,} registros en MySQL")
    except Exception as e:
        print(f"   ❌ Error insertando: {e}")

def sync_table_incremental(table_name, conn, cursor, socios_numsocio_list=None):
    """Sincronización INCREMENTAL: INSERT nuevos, UPDATE cambios"""
    print(f"\n{'='*80}")
    print(f"TABLA: {table_name}")
    print('='*80)

    # 1. Leer Access
    print(f"1. Leyendo desde Access...")
    try:
        rows = read_access_table(table_name, socios_numsocio_list)
        if not rows:
            print(f"   ⚠️  Tabla vacía")
            return
        print(f"   ✅ {len(rows):,} registros")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return
    
    # 2. Analizar columnas
    all_cols = list(OrderedDict.fromkeys(k for row in rows for k in row.keys()))
    print(f"2. Columnas: {len(all_cols)}")
    
    # 3. Verificar/crear tabla
    print(f"3. Verificando tabla...")
    cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
    table_exists = cursor.fetchone() is not None
    
    if not table_exists:
        print(f"   ℹ️  Tabla no existe, creando...")
        # Crear tabla (mismo código que sync_ALL.py)
        col_defs = ["`id` INT AUTO_INCREMENT PRIMARY KEY"]
        for col in all_cols:
            col_upper = col.upper()
            if 'FEC' in col_upper or 'DATE' in col_upper:
                col_defs.append(f"`{col}` DATETIME NULL")
            elif 'MONTO' in col_upper or 'IMPORTE' in col_upper or 'PRECIO' in col_upper:
                col_defs.append(f"`{col}` DECIMAL(15,4) NULL")
            elif 'NUM' in col_upper or 'COD' in col_upper:
                col_defs.append(f"`{col}` INT NULL")
            else:
                col_defs.append(f"`{col}` VARCHAR(255) NULL")
        
        col_defs.append("`row_hash` VARCHAR(64) NULL")
        col_defs.append("`created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        col_defs.append("`updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
        
        create_sql = f"CREATE TABLE `{table_name}` ({', '.join(col_defs)}) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
        cursor.execute(create_sql)
        print(f"   ✅ Tabla creada")
    
    # 4. Determinar columnas clave única
    unique_key_cols = get_unique_key_column(table_name, all_cols)
    print(f"4. Clave única: {' + '.join(unique_key_cols)}")
    
    # 5. Cargar registros existentes
    print(f"5. Cargando registros de MySQL...")
    existing_records = get_existing_records(cursor, table_name, unique_key_cols)
    print(f"   ✅ {len(existing_records):,} registros existentes")
    
    # 6. Clasificar operaciones
    print(f"6. Comparando datos...")
    to_insert = []
    to_update = []
    unchanged = 0
    
    for row in rows:
        # Obtener valor de la clave única (normalizado)
        if len(unique_key_cols) == 1:
            key_value = normalize_key_value(row.get(unique_key_cols[0], ''))
        else:
            # Concatenar múltiples columnas con |
            key_parts = [normalize_key_value(row.get(col, '')) for col in unique_key_cols]
            key_value = '|'.join(key_parts)
        
        # Calcular hash completo del registro
        full_hash = calculate_row_hash(row, all_cols)
        
        if key_value not in existing_records:
            # Registro nuevo (clave no existe)
            to_insert.append(row)
        else:
            # Registro existe, verificar si cambió algo
            existing_id, existing_hash = existing_records[key_value]
            if full_hash != existing_hash:
                # Hash diferente → cambió algo → UPDATE
                to_update.append((existing_id, row, full_hash))
            else:
                # Hash igual → sin cambios → SKIP
                unchanged += 1
    
    print(f"   📊 Nuevos: {len(to_insert):,} | Modificados: {len(to_update):,} | Sin cambios: {unchanged:,}")
    
    # 7. Insertar nuevos
    if to_insert:
        print(f"7. Insertando {len(to_insert):,} registros nuevos...")
        cursor.execute("SET FOREIGN_KEY_CHECKS=0")
        
        col_names = ', '.join([f'`{col}`' for col in all_cols])
        placeholders = ', '.join(['%s'] * len(all_cols))
        insert_sql = f"INSERT INTO `{table_name}` ({col_names}, row_hash) VALUES ({placeholders}, %s)"
        
        batch_size = 1000
        inserted = 0
        for i in range(0, len(to_insert), batch_size):
            batch = to_insert[i:i+batch_size]
            values = []
            for row in batch:
                row_vals = []
                for col in all_cols:
                    val = row.get(col) if row.get(col) else None
                    # Convertir fechas
                    col_upper = col.upper()
                    if val and ('FEC' in col_upper or 'FECHA' in col_upper or 'DATE' in col_upper or 
                               col_upper in ['PERLIQUIDANRO', 'F1CSOCIO', 'FBUSCAHR', 'ALTCOB', 'ALTSOCIO', 'BAJAFECHA']):
                        val = convert_date_value(val)
                    row_vals.append(val)
                row_hash = calculate_row_hash(row, all_cols)
                values.append(tuple(row_vals) + (row_hash,))
            
            try:
                cursor.executemany(insert_sql, values)
                inserted += len(batch)
            except Exception as e:
                print(f"   ⚠️  Error batch: {e}")
                for val in values:
                    try:
                        cursor.execute(insert_sql, val)
                        inserted += 1
                    except:
                        pass
        
        cursor.execute("SET FOREIGN_KEY_CHECKS=1")
        print(f"   ✅ {inserted:,} insertados")
    
    # 8. Actualizar modificados
    if to_update:
        print(f"8. Actualizando {len(to_update):,} registros modificados...")
        set_clause = ', '.join([f"`{col}` = %s" for col in all_cols])
        update_sql = f"UPDATE `{table_name}` SET {set_clause}, row_hash = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
        
        updated = 0
        for existing_id, row, row_hash in to_update:
            try:
                vals = []
                for col in all_cols:
                    val = row.get(col) if row.get(col) else None
                    # Convertir fechas
                    col_upper = col.upper()
                    if val and ('FEC' in col_upper or 'FECHA' in col_upper or 'DATE' in col_upper or 
                               col_upper in ['PERLIQUIDANRO', 'F1CSOCIO', 'FBUSCAHR', 'ALTCOB', 'ALTSOCIO', 'BAJAFECHA']):
                        val = convert_date_value(val)
                    vals.append(val)
                cursor.execute(update_sql, tuple(vals) + (row_hash, existing_id))
                updated += 1
            except Exception as e:
                pass
        
        print(f"   ✅ {updated:,} actualizados")
    
    # 9. Verificar total
    cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
    final_count = cursor.fetchone()[0]
    print(f"   📊 Total en MySQL: {final_count:,}")

# MAIN
print("="*80)
print("SINCRONIZACIÓN INCREMENTAL - COBRADOR 30")
print("="*80)

conn = get_mysql_connection()
cursor = conn.cursor()

results = {}
socios_numsocio_list = None

for table in TABLES:
    try:
        # Capturar NUMSOCIO de Socios para filtrar TbComentariosSocios
        if table == 'Socios':
            socios_rows = read_access_table('Socios')
            socios_numsocio_list = set([row.get('NUMSOCIO') for row in socios_rows if row.get('NUMSOCIO')])
            print(f"\n📋 Capturados {len(socios_numsocio_list)} NUMSOCIO de Socios para filtrar comentarios\n")

        # Verificar si esta tabla requiere FULL REFRESH
        if table in FULL_REFRESH_TABLES:
            # Leer datos de Access
            rows = read_access_table(table, socios_numsocio_list)
            # Hacer DROP/CREATE/INSERT
            sync_table_full_refresh(table, conn, cursor, rows)
        else:
            # Sincronización incremental normal
            sync_table_incremental(table, conn, cursor, socios_numsocio_list)

        cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
        count = cursor.fetchone()[0]
        results[table] = count
    except Exception as e:
        print(f"\n❌ Error en {table}: {e}")
        results[table] = 0

cursor.close()
conn.close()

# RESUMEN
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
