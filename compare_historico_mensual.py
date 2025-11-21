#!/usr/bin/env python3
"""Comparar liquidaciones por mes en los últimos 6 meses - Access vs MySQL"""

from dotenv import load_dotenv
load_dotenv()

import os
import subprocess
import csv
from io import StringIO
import mysql.connector
from datetime import datetime
from collections import defaultdict

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

def read_access_liquidaciones():
    """Leer TODAS las liquidaciones desde Access"""
    print("📂 Leyendo liquidaciones de Access...")
    
    result = subprocess.run(
        ['mdb-export', ACCESS_DB, 'Liquidaciones'],
        capture_output=True,
        text=True,
        check=True
    )
    
    reader = csv.DictReader(StringIO(result.stdout))
    rows = list(reader)
    
    return rows

def parse_fecha(fecha_str):
    """Parsear fecha en diferentes formatos"""
    if not fecha_str:
        return None
    
    for fmt in ['%m/%d/%y %H:%M:%S', '%m/%d/%Y %H:%M:%S', '%Y-%m-%d %H:%M:%S']:
        try:
            return datetime.strptime(fecha_str, fmt)
        except ValueError:
            continue
    return None

def analyze_by_month(access_rows, mysql_rows):
    """Agrupar liquidaciones por mes/año"""
    
    # Agrupar Access por mes
    access_by_month = defaultdict(lambda: {'count': 0, 'impliquida': 0, 'aboliquida': 0, 'estados': defaultdict(int)})
    
    for row in access_rows:
        fecha = parse_fecha(row.get('FECLIQUIDA', ''))
        if fecha and fecha.year >= 2024:  # Solo desde 2024
            key = f"{fecha.year}-{fecha.month:02d}"
            access_by_month[key]['count'] += 1
            
            try:
                imp = float(row.get('IMPLIQUIDA', 0) or 0)
                abo = float(row.get('ABOLIQUIDA', 0) or 0)
                access_by_month[key]['impliquida'] += imp
                access_by_month[key]['aboliquida'] += abo
            except:
                pass
            
            estado = row.get('ESTLIQUIDA', 'SIN_ESTADO')
            access_by_month[key]['estados'][estado] += 1
    
    # Agrupar MySQL por mes
    mysql_by_month = defaultdict(lambda: {'count': 0, 'impliquida': 0, 'aboliquida': 0, 'estados': defaultdict(int)})
    
    for row in mysql_rows:
        fecha = row.get('FECLIQUIDA')
        if fecha and fecha.year >= 2024:  # Solo desde 2024
            key = f"{fecha.year}-{fecha.month:02d}"
            mysql_by_month[key]['count'] += 1
            mysql_by_month[key]['impliquida'] += float(row.get('IMPLIQUIDA', 0) or 0)
            mysql_by_month[key]['aboliquida'] += float(row.get('ABOLIQUIDA', 0) or 0)
            
            estado = row.get('ESTLIQUIDA', 'SIN_ESTADO')
            mysql_by_month[key]['estados'][estado] += 1
    
    return access_by_month, mysql_by_month

def print_comparison(access_by_month, mysql_by_month):
    """Imprimir comparación mensual"""
    
    print("\n" + "="*120)
    print("📊 COMPARACIÓN MENSUAL DE LIQUIDACIONES - ÚLTIMOS MESES")
    print("="*120)
    
    # Obtener todos los meses únicos y ordenarlos
    all_months = sorted(set(list(access_by_month.keys()) + list(mysql_by_month.keys())))
    
    # Header
    print(f"\n{'MES':10s} | {'ACCESS':>8s} | {'MYSQL':>8s} | {'DIFF':>8s} | {'ACCESS $':>15s} | {'MYSQL $':>15s} | {'ESTADOS ACCESS':30s} | {'ESTADOS MYSQL':30s}")
    print("-" * 120)
    
    # Últimos 12 meses
    for month in all_months[-12:]:
        access_data = access_by_month.get(month, {'count': 0, 'aboliquida': 0, 'estados': {}})
        mysql_data = mysql_by_month.get(month, {'count': 0, 'aboliquida': 0, 'estados': {}})
        
        diff = access_data['count'] - mysql_data['count']
        diff_symbol = '✅' if diff == 0 else '⚠️'
        
        # Estados Access
        estados_access = ', '.join([f"{k}:{v}" for k, v in sorted(access_data['estados'].items())])
        if not estados_access:
            estados_access = '-'
        
        # Estados MySQL
        estados_mysql = ', '.join([f"{k}:{v}" for k, v in sorted(mysql_data['estados'].items())])
        if not estados_mysql:
            estados_mysql = '-'
        
        print(f"{month:10s} | {access_data['count']:>8,} | {mysql_data['count']:>8,} | {diff_symbol} {diff:>6,} | ${access_data['aboliquida']:>13,.2f} | ${mysql_data['aboliquida']:>13,.2f} | {estados_access:30s} | {estados_mysql:30s}")
    
    print("="*120)
    
    # Resumen
    total_access = sum(data['count'] for data in access_by_month.values())
    total_mysql = sum(data['count'] for data in mysql_by_month.values())
    
    print(f"\n📌 RESUMEN GENERAL:")
    print(f"   Total liquidaciones Access: {total_access:,}")
    print(f"   Total liquidaciones MySQL:  {total_mysql:,}")
    print(f"   Diferencia:                 {abs(total_access - total_mysql):,}")
    
    if total_access == total_mysql:
        print(f"   ✅ Las bases de datos están sincronizadas")
    else:
        print(f"   ⚠️  Hay diferencias entre las bases de datos")

def main():
    """Función principal"""
    print("="*80)
    print("ANÁLISIS HISTÓRICO MENSUAL: ACCESS vs MYSQL")
    print("="*80)
    
    try:
        # Leer de Access
        access_rows = read_access_liquidaciones()
        print(f"   ✅ {len(access_rows):,} liquidaciones totales en Access")
        
        # Leer de MySQL
        print("🗄️  Leyendo liquidaciones de MySQL...")
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
        SELECT 
            FECLIQUIDA,
            ESTLIQUIDA,
            IMPLIQUIDA,
            ABOLIQUIDA
        FROM Liquidaciones
        WHERE FECLIQUIDA IS NOT NULL
        ORDER BY FECLIQUIDA
        """
        
        cursor.execute(query)
        mysql_rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        print(f"   ✅ {len(mysql_rows):,} liquidaciones totales en MySQL")
        
        # Analizar por mes
        access_by_month, mysql_by_month = analyze_by_month(access_rows, mysql_rows)
        
        # Imprimir comparación
        print_comparison(access_by_month, mysql_by_month)
        
        print("\n" + "="*80)
        print("✅ ANÁLISIS COMPLETADO")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
