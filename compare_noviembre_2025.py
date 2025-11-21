#!/usr/bin/env python3
"""Comparar liquidaciones de Noviembre 2025 entre Access y MySQL"""

from dotenv import load_dotenv
load_dotenv()

import os
import subprocess
import csv
from io import StringIO
import mysql.connector
from datetime import datetime
from collections import Counter

ACCESS_DB = os.getenv('COBRANZA_ACCESS_PATH', '/Users/nahuel/Documents/Desarrollos/P_M_Cobranza/BBDD/Datos1.mdb')

def get_mysql_connection():
    """Conectar a MySQL"""
    config = {
        'host': os.getenv('COBRANZA_DB_HOST'),
        'user': os.getenv('COBRANZA_DB_USER'),
        'password': os.getenv('COBRANZA_DB_PASSWORD'),
        'database': os.getenv('COBRANZA_DB_NAME'),
        'port': int(os.getenv('COBRANZA_DB_PORT', 3306)),
    }
    return mysql.connector.connect(**config)

def read_access_liquidaciones_noviembre():
    """Leer liquidaciones de Noviembre 2025 desde Access"""
    print("📂 Leyendo liquidaciones de Access...")
    
    result = subprocess.run(
        ['mdb-export', ACCESS_DB, 'Liquidaciones'],
        capture_output=True,
        text=True,
        check=True
    )
    
    reader = csv.DictReader(StringIO(result.stdout))
    rows = list(reader)
    
    # Filtrar solo Noviembre 2025
    noviembre_rows = []
    for row in rows:
        fecha_str = row.get('FECLIQUIDA', '')
        if fecha_str:
            try:
                # Parsear fecha de Access: "MM/DD/YY HH:MM:SS"
                for fmt in ['%m/%d/%y %H:%M:%S', '%m/%d/%Y %H:%M:%S', '%Y-%m-%d %H:%M:%S']:
                    try:
                        dt = datetime.strptime(fecha_str, fmt)
                        if dt.year == 2025 and dt.month == 11:
                            noviembre_rows.append(row)
                        break
                    except ValueError:
                        continue
            except:
                pass
    
    return noviembre_rows

def read_mysql_liquidaciones_noviembre(conn):
    """Leer liquidaciones de Noviembre 2025 desde MySQL"""
    print("🗄️  Leyendo liquidaciones de MySQL...")
    
    cursor = conn.cursor(dictionary=True)
    
    query = """
    SELECT 
        CUPLIQUIDA,
        FECLIQUIDA,
        ESTLIQUIDA,
        IMPLIQUIDA,
        ABOLIQUIDA,
        SOCLIQUIDA,
        COBLIQUIDA,
        ZONLIQUIDA
    FROM Liquidaciones
    WHERE YEAR(FECLIQUIDA) = 2025 AND MONTH(FECLIQUIDA) = 11
    ORDER BY FECLIQUIDA
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    cursor.close()
    
    return rows

def analyze_liquidaciones(access_rows, mysql_rows):
    """Analizar diferencias entre Access y MySQL"""
    
    print("\n" + "="*80)
    print("📊 ANÁLISIS DE LIQUIDACIONES - NOVIEMBRE 2025")
    print("="*80)
    
    # Contar totales
    print(f"\n📌 TOTALES:")
    print(f"   Access: {len(access_rows):,} liquidaciones")
    print(f"   MySQL:  {len(mysql_rows):,} liquidaciones")
    
    if len(access_rows) != len(mysql_rows):
        print(f"   ⚠️  DIFERENCIA: {abs(len(access_rows) - len(mysql_rows)):,} liquidaciones")
    else:
        print(f"   ✅ Cantidades coinciden")
    
    # Análisis de estados en Access
    if access_rows:
        print(f"\n📌 ESTADOS EN ACCESS:")
        estados_access = Counter(row.get('ESTLIQUIDA', 'SIN_ESTADO') for row in access_rows)
        for estado, count in sorted(estados_access.items()):
            print(f"   {estado}: {count:,} liquidaciones")
    
    # Análisis de estados en MySQL
    if mysql_rows:
        print(f"\n📌 ESTADOS EN MYSQL:")
        estados_mysql = Counter(row.get('ESTLIQUIDA', 'SIN_ESTADO') for row in mysql_rows)
        for estado, count in sorted(estados_mysql.items()):
            print(f"   {estado}: {count:,} liquidaciones")
    
    # Análisis de fechas en Access
    if access_rows:
        print(f"\n📌 FECHAS EN ACCESS:")
        fechas_access = []
        for row in access_rows:
            fecha_str = row.get('FECLIQUIDA', '')
            if fecha_str:
                try:
                    for fmt in ['%m/%d/%y %H:%M:%S', '%m/%d/%Y %H:%M:%S', '%Y-%m-%d %H:%M:%S']:
                        try:
                            dt = datetime.strptime(fecha_str, fmt)
                            fechas_access.append(dt)
                            break
                        except ValueError:
                            continue
                except:
                    pass
        
        if fechas_access:
            fechas_access.sort()
            print(f"   Fecha mínima: {fechas_access[0].strftime('%Y-%m-%d')}")
            print(f"   Fecha máxima: {fechas_access[-1].strftime('%Y-%m-%d')}")
            
            # Contar por día
            dias = Counter(dt.strftime('%Y-%m-%d') for dt in fechas_access)
            print(f"   Días con liquidaciones: {len(dias)}")
            print(f"   Top 5 días con más liquidaciones:")
            for dia, count in dias.most_common(5):
                print(f"      {dia}: {count:,} liquidaciones")
    
    # Análisis de fechas en MySQL
    if mysql_rows:
        print(f"\n📌 FECHAS EN MYSQL:")
        fechas_mysql = [row['FECLIQUIDA'] for row in mysql_rows if row.get('FECLIQUIDA')]
        
        if fechas_mysql:
            fechas_mysql.sort()
            print(f"   Fecha mínima: {fechas_mysql[0].strftime('%Y-%m-%d')}")
            print(f"   Fecha máxima: {fechas_mysql[-1].strftime('%Y-%m-%d')}")
            
            # Contar por día
            dias = Counter(dt.strftime('%Y-%m-%d') for dt in fechas_mysql)
            print(f"   Días con liquidaciones: {len(dias)}")
            print(f"   Top 5 días con más liquidaciones:")
            for dia, count in dias.most_common(5):
                print(f"      {dia}: {count:,} liquidaciones")
    
    # Análisis de montos
    if access_rows:
        print(f"\n📌 MONTOS EN ACCESS:")
        total_imp = 0
        total_abo = 0
        for row in access_rows:
            try:
                imp = float(row.get('IMPLIQUIDA', 0) or 0)
                abo = float(row.get('ABOLIQUIDA', 0) or 0)
                total_imp += imp
                total_abo += abo
            except:
                pass
        print(f"   Total IMPLIQUIDA: ${total_imp:,.2f}")
        print(f"   Total ABOLIQUIDA: ${total_abo:,.2f}")
        print(f"   Deuda: ${total_imp - total_abo:,.2f}")
    
    if mysql_rows:
        print(f"\n📌 MONTOS EN MYSQL:")
        total_imp = sum(float(row.get('IMPLIQUIDA', 0) or 0) for row in mysql_rows)
        total_abo = sum(float(row.get('ABOLIQUIDA', 0) or 0) for row in mysql_rows)
        print(f"   Total IMPLIQUIDA: ${total_imp:,.2f}")
        print(f"   Total ABOLIQUIDA: ${total_abo:,.2f}")
        print(f"   Deuda: ${total_imp - total_abo:,.2f}")
    
    # Comparar cupones
    if access_rows and mysql_rows:
        print(f"\n📌 COMPARACIÓN DE CUPONES:")
        cupones_access = set(row.get('CUPLIQUIDA', '') for row in access_rows if row.get('CUPLIQUIDA'))
        cupones_mysql = set(str(row.get('CUPLIQUIDA', '')) for row in mysql_rows if row.get('CUPLIQUIDA'))
        
        solo_access = cupones_access - cupones_mysql
        solo_mysql = cupones_mysql - cupones_access
        
        if solo_access:
            print(f"   ⚠️  Cupones solo en Access: {len(solo_access)}")
            if len(solo_access) <= 10:
                for cup in sorted(solo_access)[:10]:
                    print(f"      - {cup}")
        
        if solo_mysql:
            print(f"   ⚠️  Cupones solo en MySQL: {len(solo_mysql)}")
            if len(solo_mysql) <= 10:
                for cup in sorted(solo_mysql)[:10]:
                    print(f"      - {cup}")
        
        if not solo_access and not solo_mysql:
            print(f"   ✅ Todos los cupones coinciden")

def main():
    """Función principal"""
    print("="*80)
    print("COMPARACIÓN LIQUIDACIONES NOVIEMBRE 2025: ACCESS vs MYSQL")
    print("="*80)
    
    try:
        # Leer de Access
        access_rows = read_access_liquidaciones_noviembre()
        
        # Leer de MySQL
        conn = get_mysql_connection()
        mysql_rows = read_mysql_liquidaciones_noviembre(conn)
        conn.close()
        
        # Analizar
        analyze_liquidaciones(access_rows, mysql_rows)
        
        print("\n" + "="*80)
        print("✅ ANÁLISIS COMPLETADO")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
