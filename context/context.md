# 📋 CONTEXT - Sistema de Migración Access → MySQL

**Proyecto:** Migración de base de datos Presencia Médica Cobranza  
**Fecha:** Noviembre 2025  
**Estado:** ✅ PRODUCCIÓN - Funcionando correctamente

---

## 🎯 OBJETIVO DEL PROYECTO

Migrar datos desde Access (.mdb) a MySQL en servidor remoto con sincronización automática, eficiente y segura.

---

## 📊 ARQUITECTURA ACTUAL

```
Access DB (Local)          →     MySQL (Remoto)
├─ Datos1.mdb             →     srv1781.hstgr.io
├─ 11 tablas              →     u596151945_cobranza
└─ 246,047 registros      →     Base de datos MySQL
```

### Stack Tecnológico:
- **Python 3.14** (stdlib: subprocess, csv, hashlib, OrderedDict)
- **mdb-tools** (lectura de Access via CLI - `mdb-export`)
- **mysql-connector-python** (conexión MySQL)
- **python-dotenv** (manejo de variables de entorno)
- **macOS** (desarrollo y testing)

**Arquitectura:** Scripts standalone sin módulos intermedios (simplicidad máxima)

---

## 🗂️ ESTRUCTURA DEL PROYECTO

```
migration_project/
├── .env                          # Configuración (credenciales)
├── .env.example                  # Template para configuración
├── requirements.txt              # Dependencias Python
├── venv_project/                 # Entorno virtual Python
│
├── sync_ALL.py                   # ⭐ Script carga completa
├── sync_INCREMENTAL.py           # ⭐ Script sincronización inteligente
├── clean_all_tables.py           # 🗑️ Limpieza de base de datos
│
├── README_SYNC.md                # 📖 Documentación de uso
└── context/
    └── context.md                # 📋 Este archivo (documentación técnica)
```

**Nota:** Estructura simplificada después de limpieza completa (Nov 2025).
- ✅ Eliminados: 40+ archivos de testing, scripts legacy, módulos no usados
- ✅ Solo archivos esenciales para sincronización
- ✅ Sin código duplicado ni módulos intermedios

---

## 📋 TABLAS MIGRADAS (10 tablas)

| Tabla | Registros (Total Access) | Registros Activos | Clave Única | Descripción | Uso |
|-------|--------------------------|-------------------|-------------|-------------|-----|
| **Liquidaciones** | 88,460 | 88,460 | CUPLIQUIDA | Liquidaciones | Crítico |
| **TbComentariosSocios** | 8,287 | 8,287 | IdComment | Comentarios de socios | Importante |
| **Socios** | 5,041 | 902 | NUMSOCIO | Socios **ACTIVOS CON CUPONES** (BAJA<>1 AND COMSOCIO='CU') | Crítico |
| **TblZonas** | 344 | 344 | NUMZONA | Zonas geográficas | Maestro |
| **TblObras** | 57 | 57 | NUNOSOCIAL | Obras sociales | Maestro |
| **TblPromotores** | 28 | 28 | NUMPROMOTOR | Promotores | Maestro |
| **Cobradores** | 26 | 26 | NUMCOB | Cobradores | Maestro |
| **TblPlanes** | 24 | 24 | NUMPLAN | Planes | Maestro |
| **TblIva** | 4 | 4 | CATIVA | Categorías IVA | Maestro |
| **TblFPagos** | 1 | 1 | NUMFPAGO | Formas de pago | Maestro |
| **TOTAL** | **102,272** | **98,133** | | | |

**Notas:**
- ⚠️ **IMPORTANTE:** PlaCobranzas fue excluida por no tener clave única natural (143,775 registros con duplicados reales)
- 🔥 **FILTROS CRÍTICOS EN SOCIOS:** Solo se sincronizan socios que cumplen **AMBAS** condiciones:
  1. **BAJA<>1** (activos, no dados de baja)
  2. **COMSOCIO='CU'** (solo socios con cupones)
  
**Distribución detallada:**
| Criterio | Cantidad | Sincroniza |
|----------|----------|------------|
| Total socios en Access | 5,041 | - |
| BAJA=1 (dados de baja) | 3,789 | ❌ EXCLUIDOS |
| BAJA<>1 (activos) | 1,252 | - |
| └─ COMSOCIO='CU' (con cupones) | 902 | ✅ SINCRONIZADOS |
| └─ COMSOCIO='FA' (factura A) | 278 | ❌ EXCLUIDOS |
| └─ COMSOCIO='FB' (factura B) | 72 | ❌ EXCLUIDOS |
| **Total sincronizado** | **902** | **✅** |
| **Reducción** | **82.1%** | - |

---

## 🚀 SCRIPTS PRINCIPALES

### 1. sync_ALL.py - Carga Completa

**Cuándo usar:** Primera carga o reseteo completo

**Qué hace:**
```python
1. Lee tabla desde Access con mdb-export
2. Analiza TODAS las columnas posibles (algunos registros tienen más columnas)
3. DROP TABLE IF EXISTS
4. CREATE TABLE con esquema dinámico
5. INSERT en batches de 1000 registros
6. Muestra progreso cada 10,000 registros
```

**Características:**
- ✅ Crea esquema automáticamente
- ✅ PK auto-increment (id)
- ✅ Timestamps (created_at, updated_at)
- ✅ Manejo de duplicados en Access
- ✅ Batching para performance
- ⚠️ Borra TODO antes de insertar

**Performance:**
- Tiempo: ~65 segundos
- Velocidad: ~3,785 registros/seg

**Comando:**
```bash
cd /Users/nahuel/Documents/Desarrollos/P_M_Cobranza/migration_project
venv_project/bin/python sync_ALL.py
```

**Logs típicos:**
```
================================================================================
TABLA: Liquidaciones
================================================================================
1. Leyendo Liquidaciones desde Access...
   ✅ 88,460 registros leídos
2. Analizando esquema...
   ✅ 17 columnas encontradas
3. Creando/recreando tabla...
   ✅ Tabla creada
4. Insertando 88,460 registros...
   ... 11,000 / 88,460
   ... 21,000 / 88,460
   ... 81,000 / 88,460
   ✅ COMPLETADO: 88,460 registros en MySQL
```

---

### 2. sync_INCREMENTAL.py - Sincronización Inteligente con Full Refresh

**Cuándo usar:** Actualizaciones diarias/horarias

**Qué hace:**
```python
1. Lee tabla desde Access
2. Detecta si la tabla requiere FULL REFRESH (ej: Socios)
   
   Para tablas con FULL REFRESH (sin clave única confiable):
   - DROP TABLE IF EXISTS
   - CREATE TABLE con esquema dinámico
   - INSERT todos los registros
   
   Para tablas normales (con clave única):
   - Carga estado actual de MySQL (id + clave_única + row_hash)
   - Para cada registro Access:
     * Calcula hash SHA-256 de TODOS los campos
     * Compara con hash guardado en MySQL (si existe)
     * Si NO existe → INSERT
     * Si hash diferente → UPDATE
     * Si hash igual → SKIP
   - Ejecuta solo INSERTs y UPDATEs necesarios
```

**Características:**
- ✅ Detección de cambios por hash (tablas normales)
- ✅ Full refresh automático para tablas sin clave única (Socios)
- ✅ Solo procesa lo modificado (tablas normales)
- ✅ No borra datos (excepto en full refresh)
- ✅ Actualiza updated_at automáticamente
- ✅ Mantiene PK auto-increment
- ✅ row_hash almacenado en MySQL
- ✅ Filtro BAJA<>1 aplicado en Socios (solo activos)

**Performance:**
- Sin cambios: ~8-10 segundos
- Con cambios: Variable (depende cantidad)

**Comando:**
```bash
cd /Users/nahuel/Documents/Desarrollos/P_M_Cobranza/migration_project
venv_project/bin/python sync_INCREMENTAL.py
```

**Logs típicos:**
```
================================================================================
TABLA: Liquidaciones
================================================================================
1. Leyendo desde Access...
   ✅ 88,460 registros
2. Columnas: 17
3. Verificando tabla...
   ✅ Tabla existe
4. Cargando estado actual de MySQL...
   ✅ 88,460 registros existentes
5. Comparando datos...
   📊 Nuevos: 5 | Modificados: 3 | Sin cambios: 88,452
6. Insertando 5 registros nuevos...
   ✅ 5 insertados
7. Actualizando 3 registros modificados...
   ✅ 3 actualizados
   📊 Total en MySQL: 88,465
```

---

## 🔑 DECISIONES TÉCNICAS IMPORTANTES

### 1. ¿Por qué PK auto-increment en lugar de usar campos originales?

**Problema descubierto:**
- Access tiene **DUPLICADOS** en las PKs originales
- Ejemplo: NUMLIQUIDA tiene 1,238 PKs duplicadas
- NUMLIQUIDA=1251 aparece 84 veces
- NUMLIQUIDA=1254 aparece 295 veces

**Solución implementada:**
```sql
CREATE TABLE Liquidaciones (
    id INT AUTO_INCREMENT PRIMARY KEY,  -- PK real
    NUMLIQUIDA INT NULL,                 -- Campo original (con duplicados)
    ... otros campos ...
    INDEX idx_numliquida (NUMLIQUIDA)    -- Índice para búsquedas
)
```

### 2. ¿Por qué no usar INSERT ... ON DUPLICATE KEY UPDATE?

**Problema:**
- ON DUPLICATE KEY solo funciona con PK o UNIQUE keys
- No podemos usar campos originales como UNIQUE (tienen duplicados)
- No sirve para detectar cambios en campos que no son clave

**Solución: Hash SHA-256**
```python
def calculate_row_hash(row, columns):
    values = []
    for col in sorted(columns):
        val = row.get(col, '')
        values.append(str(val) if val else 'NULL')
    content = '|'.join(values)
    return hashlib.sha256(content.encode()).hexdigest()
```

**Ventaja:** Detecta cambios en CUALQUIER campo, no solo PKs

### 6. ¿Por qué Socios hace FULL REFRESH en sync_INCREMENTAL.py?

**Problema descubierto:**
- NUMSOCIO no es único: muchos registros tienen valor "0"
- NUMSOCIO + NOMSOCIO tampoco es único: 11 combinaciones duplicadas detectadas
- Ejemplos: '0|ROMBOIDAL SA', '0|Tagliaferro Sergio', '0|Feliza' (duplicados)
- No hay forma confiable de identificar registros individuales

**Impacto:**
- Sync incremental fallaba: insertaba 755 "nuevos" cuando debía insertar 0
- La tabla crecía sin control (de 1,252 a 2,007 registros en una sync)

**Solución implementada:**
```python
# En sync_INCREMENTAL.py
FULL_REFRESH_TABLES = ['Socios']

# Filtros aplicados (BAJA<>1 AND COMSOCIO='CU')
TABLE_FILTERS = {
    'Socios': {
        'BAJA': '1',      # Excluir dados de baja
        'COMSOCIO': 'CU'  # Solo con cupones
    }
}

# En el loop principal:
if table in FULL_REFRESH_TABLES:
    rows = read_access_table(table)  # Lee con filtros aplicados
    sync_table_full_refresh(table, conn, cursor, rows)  # DROP/CREATE/INSERT
else:
    sync_table_incremental(table, conn, cursor)  # Hash comparison
```

**Resultado:**
- ✅ Socios siempre tiene exactamente **902 registros** (BAJA<>1 AND COMSOCIO='CU')
- ✅ Sin duplicados en MySQL
- ✅ Performance excelente: 902 registros en ~1 segundo
- ✅ Reducción del 82.1% (de 5,041 a 902)
- ⚠️ Pierde historial de `updated_at` (siempre se recrea - trade-off aceptado)

### 3. ¿Por qué autocommit=True?

**Problema encontrado:**
- Con autocommit=False, el servidor remoto daba error:
  ```
  Got error 1 "Operation not permitted" during COMMIT
  ```
- Problema de permisos del usuario MySQL en hosting compartido

**Solución:**
```python
config = {
    'autocommit': True  # Evita problemas de permisos
}
```

**Trade-off:** Menor performance transaccional, pero funciona sin errores

### 4. ¿Por qué mdb-tools en lugar de pyodbc?

**Problema:**
- pyodbc requiere drivers ODBC de Access
- En macOS es complejo instalarlo
- Requiere Wine o CrossOver

**Solución:**
```bash
mdb-export Datos1.mdb Liquidaciones > output.csv
```

**Ventajas:**
- ✅ Funciona nativamente en macOS
- ✅ No requiere drivers
- ✅ Rápido y simple
- ✅ Output CSV fácil de parsear

### 5. ¿Por qué analizar columnas de TODOS los registros?

**Problema descubierto:**
- Algunos registros tienen columnas que otros no
- Ejemplo en Liquidaciones:
  - Registro 1: 15 columnas
  - Registro 500: 17 columnas (tiene COBLIQUIDA, ABOLIQUIDA)
  
**Solución:**
```python
all_cols = set()
for row in rows:
    all_cols.update(row.keys())
all_cols = sorted(all_cols)  # 17 columnas únicas
```

**Resultado:** CREATE TABLE con TODAS las columnas posibles

---

## ⚙️ CONFIGURACIÓN (.env)

```bash
# MySQL Remoto
COBRANZA_DB_HOST=srv1781.hstgr.io
COBRANZA_DB_NAME=u596151945_cobranza
COBRANZA_DB_USER=u596151945_cobranza
COBRANZA_DB_PASSWORD=cobranzaPresencia1*
COBRANZA_DB_PORT=3306

# Access Local
COBRANZA_ACCESS_PATH=/Users/nahuel/Documents/Desarrollos/P_M_Cobranza/BBDD/Datos1.mdb

# Opcional
COBRANZA_BATCH_SIZE=1000
```

---

## 🐛 PROBLEMAS RESUELTOS

### Problema 1: Timeout en cargas grandes
**Error:** Lost connection to MySQL server during query  
**Causa:** Insertar 88K registros de una vez  
**Solución:** Batching de 1,000 registros + executemany()

### Problema 2: "Operation not permitted" en COMMIT
**Error:** Got error 1 "Operation not permitted" during COMMIT  
**Causa:** Permisos limitados en hosting compartido  
**Solución:** autocommit=True

### Problema 3: Columnas desconocidas
**Error:** Unknown column 'ABOLIQUIDA' in 'INSERT INTO'  
**Causa:** Tabla creada solo con columnas del primer registro  
**Solución:** Analizar TODOS los registros antes de CREATE TABLE

### Problema 4: PKs duplicadas
**Error:** Duplicate entry '2027' for key 'PRIMARY'  
**Causa:** Access tiene duplicados en NUMLIQUIDA  
**Solución:** PK auto-increment + campo original como INDEX

### Problema 5: INSERT IGNORE rechaza todo
**Error:** 0 registros insertados con INSERT IGNORE  
**Causa:** Todos los registros ya existían  
**Solución:** Usar sync_INCREMENTAL.py para actualizaciones

### Problema 6: Type Inference Bug - Campos DateTime no convertidos en múltiples tablas
**Síntoma:** Múltiples campos en 2 tablas tenían problemas con fechas y tipos de datos:

**Liquidaciones (7 campos):**
- `ESTLIQUIDA`: INT (todos en 0) → Debería ser VARCHAR("CA", "DE", "AD", "BO")
- `PERLIQUIDA`: INT (todos en 0) → Debería ser VARCHAR("Febrero /2022", etc.)
- `PERLIQUIDANRO`: VARCHAR (texto corrupto) → Debería ser DATETIME
- `OBSLIQUIDA`: INT (todos en 0) → Debería ser VARCHAR("-", observaciones)
- `PAGLIQUIDA`: INT (números truncados) → Debería ser VARCHAR("11/3/202", fechas cortas)
- `COMLIQUIDA`: INT (todos en 0) → Debería ser VARCHAR("N")
- `FECLIQUIDA`: NULL en todos los registros → Fechas no se convertían correctamente

**Socios (2 campos):**
- `F1CSOCIO`: INT (números sin sentido) → Debería ser DATETIME ("02/01/21 00:00:00")
- `FBuscaHR`: VARCHAR (vacío) → Debería ser DATETIME (mayormente NULL)

**Root Cause:** Tres problemas en `infer_column_type()` y `convert_date_value()`:

1. **Fechas específicas no reconocidas:** F1CSOCIO y FBuscaHR no estaban en la lista de campos DATETIME:
```python
# ❌ MAL - Solo reconocía ALTCOB, ALTSOCIO, BAJAFECHA, PERLIQUIDANRO
if col_upper in ['ALTCOB', 'ALTSOCIO', 'BAJAFECHA', 'PERLIQUIDANRO']:
    return 'DATETIME NULL'
```

Esto hacía que:
- `F1CSOCIO` → INT ❌ (debería ser DATETIME - "02/01/21 00:00:00" en Access)
- `FBuscaHR` → VARCHAR ❌ (debería ser DATETIME - mayormente NULL en Access)
- `ALTCOB` → DATETIME ✅ (correcto)
- `ALTSOCIO`, `BAJAFECHA`, `PERLIQUIDANRO`, `FechaCommet` → DATETIME ✅ (ya funcionaban)

2. **Clasificación por terminación:** Campos que terminan en "LIQUIDA" eran clasificados como INT:
```python
# ❌ MAL - Todos los *LIQUIDA como INT
elif col_upper.endswith('LIQUIDA'):
    return 'INT NULL'
```

Esto afectaba a:
- `ESTLIQUIDA` → INT ❌ (Text(2) en Access)
- `PERLIQUIDA` → INT ❌ (Text(15) en Access)
- `OBSLIQUIDA` → INT ❌ (Text(80) en Access)
- `PAGLIQUIDA` → INT ❌ (Text(10) en Access)
- `COMLIQUIDA` → INT ❌ (Text(1) en Access)
- `COBLIQUIDA` → INT ✅ (Integer en Access - correcto)
- `ZONLIQUIDA` → INT ✅ (Integer en Access - correcto)

3. **Conversión de fechas:** Las fechas de Access venían como strings "01/27/22 00:00:00" pero no se convertían a formato MySQL:
```python
# ❌ Faltaba conversión de fechas
row_values = tuple(row.get(col) for col in all_cols)
# Insertar directamente sin convertir → FECLIQUIDA quedaba NULL
```

**Root Cause Original (Problema 6 anterior):** La función `infer_column_type()` tenía lógica demasiado amplia:
```python
# ❌ MAL - Clasificaba TODO con 'COB' como DECIMAL
elif 'COB' in col_upper or 'ABO' in col_upper:
    return 'DECIMAL(15,4) NULL'
```

Esto hacía que **TODA la tabla Cobradores** tuviera campos DECIMAL:
- `NOMCOB` → DECIMAL ❌ (debería ser VARCHAR para nombres)
- `DOMCOB` → DECIMAL ❌ (debería ser VARCHAR para direcciones)
- `LOCCOB` → DECIMAL ❌ (debería ser VARCHAR para localidad)
- `COMCOB` → DECIMAL ✅ (correcto, es Double en Access)

También afectaba otras tablas:
- `SUBSOCIO` → DECIMAL por `startswith('SUB')` ❌ (debería ser INT)
- `COBLIQUIDA` → DECIMAL ❌ (debería ser INT, es Integer en Access)
- Campos con "SOCIO", "COB", etc. mal clasificados

**Solución Implementada:**
1. ❌ Eliminar condiciones ambiguas: `'COB' in`, `'ABO' in`, `startswith('SUB')`
2. ✅ Usar lógica específica y precisa:
   - **DECIMAL:** Solo `startswith('IMP')`, `endswith('MONTO')`, `'IMPORTE' in`, o lista explícita
   - **INT:** `startswith('NUM')`, `'POS'`, `'PRO'`, `'ZON'`, `'ULT'`, `endswith('COB')` con excepciones
   - **Excepciones VARCHAR:** NUMSOCIO, NUMPROMOTOR, CUPLIQUIDA (son Text en Access)
   - **Excepciones DECIMAL:** ABOLIQUIDA, COMCOB, IMPSOCIO, SUBFACTURA (campos de monto específicos)
   - **Lista INT específica:** BAJA, SUBSOCIO, POSCOB, ULTCOB, ZONCOB, ZONLIQUIDA, COBLIQUIDA, etc.

**Solución Implementada:**

1. **Agregar TODOS los campos DateTime específicos:**
```python
# sync_ALL.py y sync_INCREMENTAL.py - línea ~103
if ('FEC' in col_upper or 'FECHA' in col_upper or 'DATE' in col_upper or
    col_upper in ['ALTCOB', 'ALTSOCIO', 'BAJAFECHA', 'PERLIQUIDANRO', 'F1CSOCIO', 'FBUSCAHR']):
    return 'DATETIME NULL'
```

2. **Agregar excepciones VARCHAR específicas para Liquidaciones:**
```python
# sync_ALL.py y sync_INCREMENTAL.py - línea ~122
col_upper not in ['NUMSOCIO', 'NUMPROMOTOR', 'NUMFACTURA', 'CUPLIQUIDA', 'SOCLIQUIDA',
                   'OBSCOB', 'OBISOCIO', 'NOMCOB', 'DOMCOB', 'LOCCOB', 'TELCOB', 'CELCOB',
                   'IVACOB', 'CUICOB', 'NOMSOCIO', 'FANSOCIO', 'DOMSOCIO', 'LOCSOCIO',
                   'PROSOCIO', 'TELSOCIO', 'IVASOCIO', 'CUISOCIO', 'COMSOCIO', 'DESZONA',
                   'ESTLIQUIDA', 'PERLIQUIDA', 'OBSLIQUIDA', 'PAGLIQUIDA', 'COMLIQUIDA']
```

3. **Implementar conversión de fechas:**
```python
# Nueva función convert_date_value() en ambos archivos - línea ~140
from datetime import datetime

def convert_date_value(value):
    """Convertir fechas de formato Access a formato MySQL"""
    if not value or value == '':
        return None
    
    try:
        # Access exporta: "01/27/22 00:00:00"
        for fmt in ['%m/%d/%y %H:%M:%S', '%m/%d/%Y %H:%M:%S', '%Y-%m-%d %H:%M:%S']:
            try:
                dt = datetime.strptime(value, fmt)
                return dt.strftime('%Y-%m-%d %H:%M:%S')  # Formato MySQL
            except ValueError:
                continue
        return None
    except:
        return None
```

4. **Aplicar conversión a TODOS los campos DateTime:**
```python
# sync_ALL.py - líneas ~220 y ~240 (batch INSERT y retry)
# sync_INCREMENTAL.py - líneas ~318, ~449, ~484 (initial INSERT, new records, UPDATE)
for col in all_cols:
    val = row.get(col)
    col_upper = col.upper()
    # Aplicar conversión a TODOS los DateTime - incluyendo Socios y Liquidaciones
    if val and ('FEC' in col_upper or 'FECHA' in col_upper or 'DATE' in col_upper or 
               col_upper in ['PERLIQUIDANRO', 'F1CSOCIO', 'FBUSCAHR', 'ALTCOB', 'ALTSOCIO', 'BAJAFECHA']):
        val = convert_date_value(val)
    row_values.append(val)
```

**Resultado:**
- ✅ **Cobradores:** NUMCOB INT, NOMCOB VARCHAR, COMCOB DECIMAL, POSCOB INT, ALTCOB DATETIME
- ✅ **Socios (4 campos DateTime):** 
  - NUMSOCIO VARCHAR, NOMSOCIO VARCHAR, SUBSOCIO INT, IMPSOCIO DECIMAL
  - ALTSOCIO: DATETIME (902 registros con fechas como 2025-11-05)
  - F1CSOCIO: DATETIME (convertido de "02/01/21 00:00:00" a "2021-02-01 00:00:00")
  - BAJAFECHA: DATETIME (mayormente NULL, correcto)
  - FBuscaHR: DATETIME (mayormente NULL, correcto)
- ✅ **Liquidaciones completa (7 campos corregidos):**
  - `ESTLIQUIDA`: VARCHAR("CA": 73,241, "DE": 7,357, "AD": 7,109, "BO": 753)
  - `PERLIQUIDA`: VARCHAR("Febrero /2022", "Marzo /2016", etc.)
  - `PERLIQUIDANRO`: DATETIME (2022-02-01, 2022-03-01, etc.)
  - `OBSLIQUIDA`: VARCHAR("-", "*Telefono: 4638605", etc.)
  - `PAGLIQUIDA`: VARCHAR("--/--/--", "11/3/202", "8/4/2022", etc.)
  - `COMLIQUIDA`: VARCHAR("N": 88,460)
  - `FECLIQUIDA`: DATETIME ✅ (todas las 88,460 fechas convertidas correctamente)
  - `CUPLIQUIDA`: VARCHAR (ID único)
  - `IMPLIQUIDA/ABOLIQUIDA`: DECIMAL
  - `COBLIQUIDA/ZONLIQUIDA`: INT
- ✅ **Fechas activas:** Última fecha en base de datos: 2025-11-03 (datos recientes confirmados)
- ✅ **Sync incremental:** 0 cambios en 9 tablas (idempotencia perfecta)
- ✅ **Consultas JOIN:** Ahora funcionan correctamente con tipos compatibles

**Validación Final - Todos los DateTime verificados (7 campos en 4 tablas):**

| Tabla | Campo | Tipo Actual | Registros con datos | Ejemplo |
|-------|-------|-------------|---------------------|---------|
| Cobradores | ALTCOB | datetime | 26 | 2006-04-10 00:00:00 |
| Socios | ALTSOCIO | datetime | 902 | 2025-11-05 00:00:00 |
| Socios | F1CSOCIO | datetime ✅ | 902 | 2025-12-01 00:00:00 |
| Socios | BAJAFECHA | datetime | (mayormente NULL) | NULL |
| Socios | FBuscaHR | datetime ✅ | (mayormente NULL) | NULL |
| Liquidaciones | FECLIQUIDA | datetime | 88,460 | 2022-01-27 00:00:00 |
| Liquidaciones | PERLIQUIDANRO | datetime | 88,460 | 2022-02-01 00:00:00 |
| TbComentariosSocios | FechaCommet | datetime | 8,287 | 2011-06-21 00:00:00 |

✅ = Campos recién corregidos en esta iteración

```sql
-- Estructura completa verificada
DESCRIBE Liquidaciones;
-- 17 campos originales + id, row_hash, created_at, updated_at

-- Datos verificados
SELECT COUNT(*) FROM Liquidaciones WHERE FECLIQUIDA IS NOT NULL;  -- 88,460
SELECT DISTINCT ESTLIQUIDA FROM Liquidaciones;  -- CA, DE, AD, BO
SELECT MAX(FECLIQUIDA) FROM Liquidaciones;  -- 2025-11-03 00:00:00 ✅
```

**Cambios en código:**
```python
# sync_ALL.py y sync_INCREMENTAL.py
# 1. import datetime agregado
# 2. convert_date_value() función nueva
# 3. infer_column_type() - 5 campos agregados a excepciones VARCHAR
# 4. infer_column_type() - PERLIQUIDANRO agregado a campos DATETIME
# 5. INSERT/UPDATE - conversión de fechas aplicada
# Total: ~60 líneas nuevas/modificadas
```

**Status:** ✅ FIXED - Todos los tipos de datos alineados con Access + Conversión de fechas funcional

---

## 📈 PERFORMANCE METRICS

### sync_ALL.py
| Métrica | Valor |
|---------|-------|
| Tiempo total | ~50 segundos |
| Registros | 102,272 |
| Velocidad | ~2,045 reg/seg |
| Tablas | 10 (sin PlaCobranzas) |
| Batches | 1,000 registros |

### sync_INCREMENTAL.py
| Escenario | Tiempo | Notas |
|-----------|--------|-------|
| Sin cambios (9 tablas incrementales) | 8-10 seg | Socios hace full refresh (~1s) |
| Socios full refresh | ~1 seg | 902 registros DROP/CREATE/INSERT |
| 100 cambios (otras tablas) | 12 seg | + ~1s de Socios |
| 1,000 cambios | 20 seg | + ~1s de Socios |
| 10,000 cambios | 45 seg | + ~1s de Socios |

---

## 🔄 WORKFLOW TÍPICO

### Setup Inicial (Primera vez)
```bash
# 1. Ir al directorio del proyecto
cd /Users/nahuel/Documents/Desarrollos/P_M_Cobranza/migration_project

# 2. Carga completa inicial
/Users/nahuel/Documents/Desarrollos/P_M_Cobranza/.venv/bin/python sync_ALL.py

# Resultado: 98,133 registros en ~40 segundos
```

### Actualizaciones Diarias
```bash
# Sincronización incremental (solo cambios + Socios full refresh)
/Users/nahuel/Documents/Desarrollos/P_M_Cobranza/.venv/bin/python sync_INCREMENTAL.py

# Resultado: Solo inserta/actualiza lo modificado en ~10 segundos
```

### Si necesitas limpiar y recargar
```bash
# 1. Limpiar todas las tablas
/Users/nahuel/Documents/Desarrollos/P_M_Cobranza/.venv/bin/python clean_all_tables.py

# 2. Carga completa desde cero
/Users/nahuel/Documents/Desarrollos/P_M_Cobranza/.venv/bin/python sync_ALL.py
```

---

## 🎯 CASOS DE USO

### Caso 1: Carga inicial de base de datos
**Script:** `sync_ALL.py`  
**Frecuencia:** Una vez (o después de corrupción)
**Tiempo:** ~40 segundos (98,133 registros en 10 tablas)
**Comando:** 
```bash
/Users/nahuel/Documents/Desarrollos/P_M_Cobranza/.venv/bin/python sync_ALL.py
```

### Caso 2: Actualización diaria de datos
**Script:** `sync_INCREMENTAL.py`  
**Frecuencia:** 1-2 veces por día  
**Tiempo:** ~10 segundos (incluye Socios full refresh ~1s)
**Comando:**
```bash
/Users/nahuel/Documents/Desarrollos/P_M_Cobranza/.venv/bin/python sync_INCREMENTAL.py
```

### Caso 3: Limpieza de base de datos
**Script:** `clean_all_tables.py`  
**Frecuencia:** Cuando se necesita resetear todo  
**Tiempo:** ~2 segundos (DROP 10 tablas)
**Comando:**
```bash
/Users/nahuel/Documents/Desarrollos/P_M_Cobranza/.venv/bin/python clean_all_tables.py
```

### Caso 4: Automatización con cron
**Frecuencia:** Cada 5-10 minutos o diaria  
**Configuración:**
```bash
# Editar crontab
crontab -e

# Sincronización cada 10 minutos
*/10 * * * * /Users/nahuel/Documents/Desarrollos/P_M_Cobranza/.venv/bin/python /Users/nahuel/Documents/Desarrollos/P_M_Cobranza/migration_project/sync_INCREMENTAL.py >> /tmp/sync.log 2>&1

# O una vez al día a las 6am
0 6 * * * /Users/nahuel/Documents/Desarrollos/P_M_Cobranza/.venv/bin/python /Users/nahuel/Documents/Desarrollos/P_M_Cobranza/migration_project/sync_INCREMENTAL.py >> /tmp/sync.log 2>&1
```

---

## � FILTROS DE DATOS CRÍTICOS

### Filtros de Socios: Activos + Con Cupones

**REGLA FUNDAMENTAL:** Solo se sincronizan socios **activos con cupones** (BAJA<>1 AND COMSOCIO='CU').

**Implementación:**
```python
# En sync_ALL.py y sync_INCREMENTAL.py
TABLE_FILTERS = {
    'Socios': {
        'BAJA': '1',      # Excluir socios dados de baja
        'COMSOCIO': 'CU'  # Solo socios con cupones
    }
}

# En read_access_table()
if table_name == 'Socios' and isinstance(filters, dict):
    # Filtro 1: BAJA<>1
    if 'BAJA' in filters:
        exclude_value = filters['BAJA']
        rows = [row for row in rows if row.get('BAJA') != exclude_value]
    
    # Filtro 2: COMSOCIO='CU'
    if 'COMSOCIO' in filters:
        required_value = filters['COMSOCIO']
        rows = [row for row in rows if row.get('COMSOCIO') == required_value]
```

**Distribución de registros:**
| Filtro | Cantidad | Se sincroniza |
|--------|----------|---------------|
| Total Access | 5,041 | - |
| `BAJA=1` (dados de baja) | 3,789 | ❌ NO |
| `BAJA<>1` (activos) | 1,252 | → |
| └─ `COMSOCIO='CU'` (cupones) | 902 | ✅ SÍ |
| └─ `COMSOCIO='FA'` (factura A) | 278 | ❌ NO |
| └─ `COMSOCIO='FB'` (factura B) | 72 | ❌ NO |
| **Total sincronizados** | **902** | ✅ |

**Motivos de los filtros:**
1. **BAJA<>1:** Excluir socios dados de baja (lógica de negocio)
2. **COMSOCIO='CU':** Solo socios que pagan con cupones (no factura A/B)
3. **Performance:** Reduce 82.1% el tamaño (de 5,041 a 902 registros)
4. **Consistencia:** Evita duplicados (muchos con BAJA=1 tienen NUMSOCIO=0)

**Aplicación:**
- ✅ Se aplica en `sync_ALL.py` (carga inicial)
- ✅ Se aplica en `sync_INCREMENTAL.py` (actualizaciones)
- ⚠️ **IMPORTANTE:** Socios hace **FULL REFRESH** en cada sync_INCREMENTAL.py:
  - Se hace DROP TABLE + CREATE TABLE + INSERT
  - Siempre queda con exactamente **902 registros** (BAJA<>1 AND COMSOCIO='CU')
  - Si un socio cambia BAJA=0 → BAJA=1: **desaparece** de MySQL en próxima sync
  - Si un socio cambia BAJA=1 → BAJA=0: **aparece** en MySQL en próxima sync
  - Si un socio cambia COMSOCIO='CU' → 'FA': **desaparece** de MySQL
  - Si un socio cambia COMSOCIO='FA' → 'CU': **aparece** en MySQL
  - No hay registros "fantasma" (a diferencia de otras tablas con sync incremental)

---

## �🔐 SEGURIDAD

### Credenciales
- ✅ Almacenadas en .env (no en código)
- ✅ .env en .gitignore
- ⚠️ Credenciales hardcodeadas eliminadas de scripts legacy

### Validaciones
- ✅ Nombres de tabla validados (SecurityValidator)
- ✅ Nombres de columna validados (regex)
- ✅ SQL injection prevenido (prepared statements)
- ✅ Paths validados (SecurityValidator)

### Conexión
- ✅ SSL/TLS habilitado por defecto
- ✅ Timeout configurado (30 segundos)
- ✅ Connection pooling deshabilitado (autocommit=True)

---

## � RELACIONES ENTRE TABLAS VERIFICADAS

**Estado:** ✅ Todas las relaciones verificadas y compatibles

### Relaciones Principales

| Relación | Campo Origen | Campo Destino | Tipo Datos | Estado |
|----------|--------------|---------------|------------|--------|
| **Socios → Liquidaciones** | Socios.NUMSOCIO | Liquidaciones.SOCLIQUIDA | VARCHAR(255) ↔ VARCHAR(255) | ✅ Compatible |
| **Cobradores → Liquidaciones** | Cobradores.NUMCOB | Liquidaciones.COBLIQUIDA | INT(11) ↔ INT(11) | ✅ Compatible |
| **TbComentariosSocios → Socios** | TbComentariosSocios.NUMSOCIO | Socios.NUMSOCIO | VARCHAR(255) ↔ VARCHAR(255) | ✅ Compatible |

### Queries de Ejemplo Validados

**1. Socios con sus Liquidaciones:**
```sql
SELECT S.NUMSOCIO, S.NOMSOCIO, L.CUPLIQUIDA, L.IMPLIQUIDA
FROM Socios S
JOIN Liquidaciones L ON S.NUMSOCIO = L.SOCLIQUIDA
LIMIT 10;
```

**2. Cobradores con sus Liquidaciones:**
```sql
SELECT C.NUMCOB, C.NOMCOB, L.CUPLIQUIDA, L.IMPLIQUIDA
FROM Cobradores C
JOIN Liquidaciones L ON C.NUMCOB = L.COBLIQUIDA
LIMIT 10;
```

**3. Comentarios de Socios:**
```sql
SELECT C.IdComment, C.NUMSOCIO, S.NOMSOCIO, C.Comment
FROM TbComentariosSocios C
JOIN Socios S ON C.NUMSOCIO = S.NUMSOCIO
WHERE C.Baja = 0
LIMIT 10;
```

**4. Query Completo (Liquidaciones + Cobradores + Socios):**
```sql
SELECT 
    L.CUPLIQUIDA,
    L.IMPLIQUIDA,
    C.NOMCOB AS Cobrador,
    S.NOMSOCIO AS Socio
FROM Liquidaciones L
LEFT JOIN Cobradores C ON L.COBLIQUIDA = C.NUMCOB
LEFT JOIN Socios S ON L.SOCLIQUIDA = S.NUMSOCIO
LIMIT 10;
```

### Verificación de Tipos (19 Nov 2025)

**Antes de la corrección:**
- ❌ Cobradores.NUMCOB (INT) vs Liquidaciones.COBLIQUIDA (DECIMAL) → Conversión implícita
- ⚠️ JOIN funcionaba pero con overhead de conversión de tipos

**Después de la corrección:**
- ✅ Cobradores.NUMCOB (INT) vs Liquidaciones.COBLIQUIDA (INT) → Tipos idénticos
- ✅ JOIN óptimo sin conversiones
- ✅ Alineado con Access: COBLIQUIDA es Integer en Datos1.mdb

**Testing realizado:**
```bash
# Verificación de tipos
DESCRIBE Cobradores;     # NUMCOB: int(11)
DESCRIBE Liquidaciones;  # COBLIQUIDA: int(11) ✅

# Prueba de JOINs (todos exitosos)
- Socios ↔ Liquidaciones: 3 filas
- Cobradores ↔ Liquidaciones: 5 filas  
- TbComentariosSocios ↔ Socios: 3 filas
```

---

## �📝 ESQUEMA DE TABLA TIPO

```sql
CREATE TABLE Liquidaciones (
    -- PK auto-increment
    id INT AUTO_INCREMENT PRIMARY KEY,
    
    -- Campos originales de Access
    NUMLIQUIDA INT NULL,
    FECLIQUIDA DATETIME NULL,
    NUMSOCIO INT NULL,
    CUOTALIQ INT NULL,
    OBSERVACION VARCHAR(255) NULL,
    MONTO DECIMAL(15,4) NULL,
    COBLIQUIDA DECIMAL(15,4) NULL,
    ABOLIQUIDA DECIMAL(15,4) NULL,
    -- ... más campos según Access
    
    -- Campos de control
    row_hash VARCHAR(64) NULL,                    -- Hash para detectar cambios
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Índices
    INDEX idx_numliquida (NUMLIQUIDA)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

## 🚨 LIMITACIONES CONOCIDAS

### 1. Matching de registros
- **Limitación:** sync_INCREMENTAL usa la primera columna como "clave lógica"
- **Impacto:** Si hay múltiples registros con el mismo valor en columna 1, puede no matchear correctamente
- **Solución futura:** Permitir configurar columnas para matching

### 2. Deletes no manejados
- **Limitación:** Si borras un registro en Access, NO se borra en MySQL
- **Impacto:** MySQL puede tener registros "fantasma"
- **Solución futura:** Flag de "eliminado" o sincronización bidireccional

### 3. Esquema fijo
- **Limitación:** Si Access agrega una columna nueva, hay que re-crear tabla
- **Impacto:** sync_INCREMENTAL fallará con "Unknown column"
- **Solución:** Ejecutar sync_ALL.py para recrear esquema

### 4. Tipos de datos inferidos
- **Limitación:** Tipos se infieren por nombre de columna, no por contenido
- **Impacto:** Puede asignar VARCHAR a un campo numérico si no tiene prefijo típico
- **Workaround:** Los INSERTs funcionan igual (conversión automática)

### 5. Socios hace full refresh en cada sync
- **Limitación:** Tabla Socios se recrea completamente en cada sync_INCREMENTAL.py
- **Impacto:** 
  - No hay tracking de cambios individuales
  - Se pierde `updated_at` histórico
  - ~1 segundo adicional por sync (902 registros con filtros)
- **Motivo:** No tiene clave única confiable (NUMSOCIO y NUMSOCIO+NOMSOCIO tienen duplicados)
- **Filtros aplicados:** Solo socios activos con cupones (BAJA<>1 AND COMSOCIO='CU')
- **Trade-off aceptado:** Preferencia por consistencia de datos sobre historial de cambios

---

## 🔮 MEJORAS FUTURAS

### Alta prioridad
- [x] Agregar columna row_hash a sync_ALL.py ✅
- [x] Configurar columnas de matching en sync_INCREMENTAL ✅
- [x] Implementar full refresh para tablas sin clave única ✅
- [ ] Manejo de deletes (soft delete)
- [ ] Logs a archivo (además de stdout)

### Media prioridad
- [ ] Automatización con cron/systemd
- [ ] Notificaciones por email en errores
- [ ] Dashboard web de estado
- [ ] Rollback automático si falla

### Baja prioridad
- [ ] GUI para configuración
- [ ] Soporte para múltiples bases Access
- [ ] Exportar a otros formatos (PostgreSQL, MongoDB)
- [ ] Compresión de datos históricos

---

## 📚 DOCUMENTACIÓN ADICIONAL

- `README_SYNC.md` - Guía de uso completa con ejemplos
- `demo_incremental.py` - Script demostrativo interactivo
- Logs en terminal - Detallados y con emojis

---

## 🛠️ COMANDOS ÚTILES

### Comandos de Access (mdb-tools)
```bash
# Ver todas las tablas en Access
mdb-tables /Users/nahuel/Documents/Desarrollos/P_M_Cobranza/BBDD/Datos1.mdb

# Exportar tabla específica a CSV
mdb-export /Users/nahuel/Documents/Desarrollos/P_M_Cobranza/BBDD/Datos1.mdb Liquidaciones

# Ver esquema SQL de Access
mdb-schema /Users/nahuel/Documents/Desarrollos/P_M_Cobranza/BBDD/Datos1.mdb

# Contar registros en Access
mdb-export /Users/nahuel/Documents/Desarrollos/P_M_Cobranza/BBDD/Datos1.mdb Socios | tail -n +2 | wc -l
```

### Comandos de MySQL (remoto)
```bash
# Contar registros en una tabla
mysql -h srv1781.hstgr.io -u u596151945_cobranza -p u596151945_cobranza -e "SELECT COUNT(*) FROM Liquidaciones;"

# Ver últimas actualizaciones
mysql -h srv1781.hstgr.io -u u596151945_cobranza -p u596151945_cobranza -e "SELECT * FROM Liquidaciones ORDER BY updated_at DESC LIMIT 10;"

# Ver todas las tablas
mysql -h srv1781.hstgr.io -u u596151945_cobranza -p u596151945_cobranza -e "SHOW TABLES;"

# Ver resumen de todas las tablas
mysql -h srv1781.hstgr.io -u u596151945_cobranza -p u596151945_cobranza -e "
SELECT table_name, table_rows 
FROM information_schema.tables 
WHERE table_schema='u596151945_cobranza' 
ORDER BY table_rows DESC;"
```

### Scripts del proyecto
```bash
# Limpiar base de datos
/Users/nahuel/Documents/Desarrollos/P_M_Cobranza/.venv/bin/python clean_all_tables.py

# Carga completa
/Users/nahuel/Documents/Desarrollos/P_M_Cobranza/.venv/bin/python sync_ALL.py

# Sincronización incremental
/Users/nahuel/Documents/Desarrollos/P_M_Cobranza/.venv/bin/python sync_INCREMENTAL.py
```

---

## 📞 MANTENIMIENTO Y EVOLUCIÓN

**Proyecto:** Migración Access → MySQL Presencia Médica Cobranza  
**Cliente:** Nahuel  
**Fecha:** Noviembre 2025  
**Versión:** 2.0 PRODUCCIÓN (Post-Limpieza)

**Historial de versiones:**
- **v1.0** (Nov 2025): Sistema inicial funcionando con módulos legacy
- **v2.0** (Nov 2025): **LIMPIEZA COMPLETA** - Ver sección abajo

---

## 🧹 LIMPIEZA COMPLETA DEL PROYECTO (v2.0 - Nov 2025)

### Objetivo
Dejar el repositorio lo más simple, claro y liviano posible, sin archivos muertos, código duplicado ni estructuras que no se usan.

### Archivos Eliminados (40+ archivos)

#### Scripts de Testing (13 archivos):
```
test_check_hash.py
test_connectivity.py  
test_fast.py
test_full_migration.py
test_liq_small_batch.py
test_liquidaciones.py
test_mdbtools.py
test_mysql.py
test_read_access.py
test_setup.py
test_sync_incomplete.py
demo_access_data.py
demo_incremental.py
```

#### Scripts Legacy/No Usados (11 archivos):
```
main.py - Arquitectura vieja con módulos
sync_NOW.py - Duplicado
sync_liquidaciones_fast.py - Experimento viejo
drop_liquidaciones.py - Específico innecesario
drop_tables.py - Similar a clean_all_tables.py
drop_unused_tables.py - Viejo
reset_liquidaciones.py - Específico innecesario
install.sh - No usado
check_missing.py
check_pk_ranges.py
compare_counts.py
```

#### Módulos Completos (5 carpetas - 12+ archivos):
```
access/ - No usado por scripts principales
mysql_writer/ - No usado por scripts principales
config/ - No usado por scripts principales
security/ - No usado por scripts principales
sync/ - No usado por scripts principales
```

#### Otros (5 archivos):
```
__init__.py (raíz)
SECURITY.md
README.md (duplicado con README_SYNC.md)
migration_secure.log
venv/ (entorno virtual duplicado)
```

### Resultado
- **Archivos eliminados:** ~40
- **Carpetas eliminadas:** 6 (incluyendo venv duplicado)
- **Reducción:** ~80% de archivos
- **Scripts mantenidos:** 3 esenciales (sync_ALL, sync_INCREMENTAL, clean_all_tables)
- **Arquitectura:** Scripts standalone sin módulos intermedios (máxima simplicidad)

**Para actualizar este context.md:**
1. Agregar nuevos problemas resueltos en sección correspondiente
2. Actualizar métricas de performance cuando cambien
3. Documentar nuevas features o filtros
4. Mantener "REGLAS DE ORO" intactas (inmutables)
5. Agregar lecciones aprendidas en decisiones técnicas

**Archivos críticos del proyecto:**
- `sync_ALL.py` - Nunca modificar lógica de hashing
- `sync_INCREMENTAL.py` - Nunca modificar FULL_REFRESH_TABLES sin análisis
- `clean_all_tables.py` - Verificar TABLES list antes de modificar
- `context/context.md` - Este archivo (mantener actualizado)

---

## ✅ CHECKLIST DE DESPLIEGUE Y CALIDAD

### Funcionalidad
- [x] Scripts funcionando correctamente
- [x] sync_ALL.py: 98,133 registros en ~40 segundos
- [x] sync_INCREMENTAL.py: Detección de cambios + Socios full refresh
- [x] clean_all_tables.py: Limpieza completa de MySQL
- [x] Filtros de Socios: BAJA<>1 AND COMSOCIO='CU' (902 registros)

### Documentación
- [x] Documentación técnica completa (context.md)
- [x] Documentación de usuario (README_SYNC.md)
- [x] Casos de uso documentados con comandos exactos
- [x] Decisiones técnicas explicadas
- [x] Limitaciones conocidas documentadas

### Configuración
- [x] Credenciales en .env (no en código)
- [x] .env.example disponible como template
- [x] requirements.txt actualizado
- [x] Paths absolutos en comandos de ejemplo

### Performance
- [x] Batching de 1,000 registros
- [x] Hash SHA-256 para detección de cambios
- [x] Diccionario en memoria O(1)
- [x] Full refresh optimizado para Socios (~1 segundo)

### Calidad de Código
- [x] Sin archivos muertos (40+ eliminados)
- [x] Sin código duplicado
- [x] Sin módulos intermedios innecesarios
- [x] Estructura de proyecto simplificada
- [x] Solo 3 scripts principales (+ requirements + docs)

### Mantenimiento
- [x] Context.md actualizado post-limpieza
- [x] Reglas de oro documentadas
- [x] Comandos útiles para troubleshooting
- [x] Historial de versiones
- [x] Guía de automatización con cron

---

## 🔑 MAPEO DE CLAVES ÚNICAS

**REGLA FUNDAMENTAL:** Cada tabla tiene un campo ID único en Access que se usa para identificar registros en sync incremental.

### Claves Verificadas ✅

| Tabla | Campo Único | Verificación | Observaciones |
|-------|-------------|--------------|---------------|
| **Cobradores** | `NUMCOB` | ✅ 26 únicos / 26 total | 100% único |
| **Socios** | **FULL REFRESH** | ❌ Sin clave única confiable | DROP/CREATE en cada sync<br>NUMSOCIO tiene duplicados<br>NUMSOCIO+NOMSOCIO tiene 11 duplicados |
| **Liquidaciones** | `CUPLIQUIDA` | ✅ 88,460 únicos / 88,460 total | 100% único - Confirmado por usuario |
| **TblObras** | `NUNOSOCIAL` | ✅ 57 únicos / 57 total | 100% único |
| **TblPlanes** | `NUMPLAN` | ✅ 24 únicos / 24 total | 100% único |

### Claves Por Verificar ⚠️

| Tabla | Campo Único Asumido | Estado |
|-------|---------------------|--------|
| **TblFPagos** | `NUMFPAGO` | ⚠️ Por verificar |
| **TblIva** | `CATIVA` | ⚠️ Por verificar |
| **TblZonas** | `NUMZONA` | ⚠️ Por verificar |
| **TblPromotores** | `NUMPROMOTOR` | ⚠️ Por verificar |
| **TbComentariosSocios** | `IdComment` | ⚠️ Por verificar |

### Tablas Excluidas ❌

| Tabla | Motivo | Detalles |
|-------|--------|----------|
| **PlaCobranzas** | No tiene clave única | PLACOB: 1,959 únicos / 143,775 total<br>CUPCOB: 138,791 únicos / 143,775 total<br>Ninguna combinación es única<br>Tiene 3,618 duplicados reales |

**Implementación en código:**
```python
# sync_INCREMENTAL.py
key_map = {
    'Cobradores': ['NUMCOB'],
    'Socios': ['NUMSOCIO', 'NOMSOCIO'],  # ⚠️ NO USADO - Tabla en FULL_REFRESH_TABLES
    'Liquidaciones': ['CUPLIQUIDA'],
    'TblObras': ['NUNOSOCIAL'],
    'TblPlanes': ['NUMPLAN'],
    'TblFPagos': ['NUMFPAGO'],
    'TblIva': ['CATIVA'],
    'TblZonas': ['NUMZONA'],
    'TblPromotores': ['NUMPROMOTOR'],
    'TbComentariosSocios': ['IdComment']
}

# Tablas que hacen FULL REFRESH en cada sync (DROP/CREATE)
FULL_REFRESH_TABLES = ['Socios']
```

---

## 🔄 LÓGICA DE SINCRONIZACIÓN INCREMENTAL

### Estrategia de Comparación por Hash

**Objetivo:** Detectar cambios en registros sin hacer SELECT por cada fila (performance O(1))

**Flujo:**
```
1. Cargar estado de MySQL en memoria:
   → SELECT id, clave_unica, row_hash FROM tabla
   → Crear diccionario: {clave_unica: (id, row_hash)}
   
2. Leer todos los registros desde Access
   
3. Para cada registro de Access:
   a. Calcular row_hash (SHA-256 de todos los campos ordenados)
   b. Obtener valor de clave_unica
   c. Buscar en diccionario:
      
      Si clave_unica NO existe:
        → INSERT (registro nuevo)
      
      Si clave_unica existe:
        → Comparar row_hash con el guardado
        
        Si hash diferente:
          → UPDATE (algo cambió)
        
        Si hash igual:
          → SKIP (sin cambios)
```

### Función calculate_row_hash()

```python
def calculate_row_hash(row, columns):
    """
    Calcula hash SHA-256 de una fila para detectar cambios.
    
    - Ordena columnas alfabéticamente (consistencia)
    - Convierte NULL a 'NULL' string
    - Une valores con '|' como separador
    - Genera hash de 64 caracteres
    """
    values = []
    for col in sorted(columns):
        val = row.get(col, '')
        values.append(str(val) if val else 'NULL')
    content = '|'.join(values)
    return hashlib.sha256(content.encode()).hexdigest()
```

### Ventajas de esta Estrategia

1. **Performance:** 
   - 1 solo SELECT para toda la tabla
   - Comparación O(1) en diccionario Python
   - No hay N queries individuales

2. **Detección precisa:**
   - Detecta cambios en CUALQUIER campo
   - No requiere timestamp de última modificación
   - Hash cambia si cualquier valor cambia

3. **Idempotente:**
   - Ejecutar múltiples veces produce mismo resultado
   - No hay duplicados si re-ejecutas
   - Safe para automatización

### Ejemplo de Ejecución

```
TABLA: Liquidaciones
1. Leyendo desde Access...
   ✅ 88,460 registros
2. Columnas: 17
3. Verificando tabla...
   ✅ Tabla existe
4. Clave única: CUPLIQUIDA
5. Cargando registros de MySQL...
   ✅ 88,460 registros existentes
6. Comparando datos...
   📊 Nuevos: 0 | Modificados: 0 | Sin cambios: 88,460
```

### Performance Metrics

| Operación | Tiempo | Registros |
|-----------|--------|-----------|
| Cargar estado MySQL | ~0.5 seg | 88,460 |
| Leer Access | ~2 seg | 88,460 |
| Calcular hashes | ~1 seg | 88,460 |
| Comparar | ~0.1 seg | 88,460 |
| **Total (sin cambios)** | **~4 seg** | **88,460** |

Si hay cambios:
- INSERT: ~50 ms por 1,000 registros (executemany)
- UPDATE: ~100 ms por 1,000 registros (individual)

---

## 🎯 REGLAS DE ORO DEL PROYECTO

**Principios fundamentales que NUNCA deben violarse:**

1. **Mantener idempotencia siempre:** Nunca borrar registros excepto que se pida explícitamente
2. **Nunca hacer SELECT por fila en sincronización:** Siempre usar diccionario en memoria
3. **Nunca recrear índices en cada sync:** Solo después de cargas iniciales
4. **Mantener hashing consistente en todas las tablas:** SHA-256 con mismo algoritmo
5. **Todas las sincronizaciones deben procesarse en batches:** Entre 100 y 500 registros
6. **Estrictamente prohibido cambiar PKs sin decisión explícita:** Los PKs son inmutables
7. **Todas las cargas deben realizarse dentro de una transacción:** Atomicidad garantizada
8. **Commits solo por lote o al finalizar la tabla:** Nunca commit por registro
9. **No introducir borrados automáticos:** Preservar datos siempre
10. **Los scripts deben ser deterministas, reproducibles y medibles:** Mismos datos = mismo resultado

---

## 🗺️ MAPA DEL FLUJO DE SINCRONIZACIÓN

**Proceso paso a paso de cómo funciona la sincronización:**

### 1. Leer configuración desde .env
```python
# Cargar credenciales y rutas
COBRANZA_DB_HOST, COBRANZA_DB_NAME, COBRANZA_ACCESS_PATH, etc.
```

### 2. Abrir conexión a Access (.accdb o .mdb)
```python
# Usando mdb-export via subprocess
subprocess.run(['mdb-export', access_path, table_name])
```

### 3. Detectar tablas habilitadas
```python
# Lista de 11 tablas a sincronizar
tables = ['Cobradores', 'Socios', 'PlaCobranzas', 'Liquidaciones', ...]
```

### 4. Para cada tabla:

#### 4.1 Cargar filas existentes de MySQL en un diccionario
```python
# {pk → row_hash} para comparación rápida O(1)
existing_records = {}
rows = cursor.execute("SELECT id, row_hash FROM tabla")
for row in rows:
    existing_records[row['id']] = row['row_hash']
```

#### 4.2 Leer registros desde Access
```python
# Exportar tabla completa a CSV
csv_data = mdb_export(table_name)
records = parse_csv(csv_data)
```

#### 4.3 Dividir en lotes
```python
# Batches de 1000 registros
batch_size = 1000
batches = [records[i:i+batch_size] for i in range(0, len(records), batch_size)]
```

#### 4.4 Para cada lote:
```python
inserts = []
updates = []

for record in batch:
    # Calcular hash por fila
    row_hash = calculate_row_hash(record, columns)
    
    # Comparar contra el diccionario
    if pk not in existing_records:
        inserts.append(record)  # Nuevo registro
    elif existing_records[pk] != row_hash:
        updates.append(record)  # Registro modificado
    else:
        # SKIP - registro sin cambios
        pass
```

#### 4.5 Ejecutar inserciones y actualizaciones dentro de una transacción
```python
# Con autocommit=True, cada executemany es una transacción
if inserts:
    cursor.executemany("INSERT INTO ...", inserts)
if updates:
    cursor.executemany("UPDATE ... WHERE id=?", updates)
```

#### 4.6 Hacer commit
```python
# Con autocommit=True, commit automático por batch
# Sin autocommit: connection.commit()
```

### 5. Generar métricas de performance
```python
print(f"✅ COMPLETADO: {total_records} registros en {elapsed_time:.2f} segundos")
print(f"📊 Nuevos: {new_count} | Modificados: {modified_count} | Sin cambios: {unchanged_count}")
```

### 6. Crear índices solo en la carga inicial
```python
# En sync_ALL.py: CREATE INDEX después de INSERT
# En sync_INCREMENTAL.py: NO crear índices (ya existen)
```

---

## ⛔ NO HACER NUNCA

**Anti-patrones y prácticas prohibidas:**

### ❌ No usar SELECT por registro individual
```python
# MAL ❌
for record in access_records:
    cursor.execute("SELECT * FROM tabla WHERE id = %s", (record['id'],))
    existing = cursor.fetchone()
    # 88,460 SELECTs = LENTÍSIMO

# BIEN ✅
existing_records = {row['id']: row for row in cursor.execute("SELECT * FROM tabla")}
for record in access_records:
    existing = existing_records.get(record['id'])
    # 1 SELECT total = RÁPIDO
```

### ❌ No hacer INSERT o UPDATE fuera de transacciones
```python
# MAL ❌
for record in records:
    cursor.execute("INSERT INTO ...", record)  # Sin transacción

# BIEN ✅
cursor.executemany("INSERT INTO ...", records)  # Batch dentro de transacción
```

### ❌ No modificar PKs sin indicación explícita
```python
# MAL ❌
UPDATE tabla SET id = id + 1000 WHERE ...  # ¡Rompe referencias!

# BIEN ✅
# Los PKs NUNCA se modifican
```

### ❌ No agregar lógica de borrado automático
```python
# MAL ❌
# Si un registro no está en Access, borrarlo de MySQL
if pk not in access_records:
    cursor.execute("DELETE FROM tabla WHERE id = %s", (pk,))

# BIEN ✅
# Los registros en MySQL se preservan SIEMPRE
# Solo INSERT y UPDATE, nunca DELETE
```

### ❌ No mezclar sync ALL con sync incremental en un mismo run
```python
# MAL ❌
if is_first_run:
    sync_all()
else:
    sync_incremental()  # En el mismo script

# BIEN ✅
# sync_ALL.py - Script separado para carga completa
# sync_INCREMENTAL.py - Script separado para actualizaciones
```

### ❌ No reactivar índices antes de terminar la carga masiva
```python
# MAL ❌
CREATE INDEX idx_campo ...
INSERT INTO tabla ...  # Lento porque actualiza índice por cada INSERT

# BIEN ✅
INSERT INTO tabla ...  # Rápido sin índices
CREATE INDEX idx_campo ...  # Índice al final
```

---

## 📖 GLOSARIO

**Términos técnicos del proyecto:**

| Término | Definición | Ejemplo |
|---------|------------|---------|
| **PK** | Primary Key - Clave primaria utilizada para identificar registros únicos | `id INT AUTO_INCREMENT PRIMARY KEY` |
| **Row Hash** | Hash SHA-256 generado por fila para detectar cambios en cualquier campo | `abc123def456...` (64 caracteres) |
| **Batch** | Tamaño del grupo de registros que se procesa por iteración | 1,000 registros por batch |
| **Full Sync / ALL** | Carga masiva inicial sin índices, con DROP TABLE y CREATE TABLE | `sync_ALL.py` |
| **Incremental Sync** | Actualización diaria que compara hashes para detectar cambios | `sync_INCREMENTAL.py` |
| **Diccionario en memoria** | Estructura `{pk: row_hash}` utilizada para comparación rápida O(1) | `{1: 'abc123', 2: 'def456'}` |
| **Tabla crítica** | Tabla con más de 10k registros (como PlaCobranzas o Liquidaciones) | 88,460+ registros |
| **executemany()** | Método MySQL para insertar múltiples registros en una sola operación | `cursor.executemany(sql, records)` |
| **autocommit** | Modo donde cada operación SQL se confirma automáticamente | `autocommit=True` |
| **mdb-export** | Herramienta CLI de mdb-tools para exportar tablas Access a CSV | `mdb-export Datos1.mdb Liquidaciones` |
| **Idempotencia** | Propiedad donde ejecutar múltiples veces produce el mismo resultado | Re-ejecutar sync no duplica datos |
| **SHA-256** | Algoritmo de hash criptográfico usado para detectar cambios en datos | `hashlib.sha256(content.encode()).hexdigest()` |

---

---

## 📊 ESTADO ACTUAL DEL PROYECTO

**Estado:** ✅ COMPLETADO Y VALIDADO - Sistema en producción con tipos de datos correctos

**Últimas actualizaciones (20 Nov 2025):**
- ✅ Claves únicas mapeadas correctamente
- ✅ CUPLIQUIDA confirmado como ID único de Liquidaciones
- ✅ PlaCobranzas excluida (sin clave única natural)
- ✅ row_hash implementado en todas las tablas
- ✅ Lógica de comparación optimizada (diccionario en memoria)
- ✅ **Filtro BAJA<>1 AND COMSOCIO='CU' implementado en Socios** (902 de 5,041)
- ✅ Filtros aplicados en sync_ALL.py y sync_INCREMENTAL.py
- ✅ **Full refresh implementado para Socios** (sin clave única confiable)
- ✅ sync_INCREMENTAL.py detecta automáticamente tablas FULL_REFRESH_TABLES
- ✅ **Bug de tipos de datos RESUELTO** - infer_column_type() reescrita completamente
- ✅ **Todos los tipos validados:** INT, VARCHAR, DECIMAL, DATETIME correctos
- ✅ **COBLIQUIDA corregido:** DECIMAL → INT (alineado con Access Integer)
- ✅ **Liquidaciones: 7 campos corregidos** - ESTLIQUIDA, PERLIQUIDA, PERLIQUIDANRO, OBSLIQUIDA, PAGLIQUIDA, COMLIQUIDA, FECLIQUIDA
- ✅ **Socios: 2 campos DateTime corregidos** - F1CSOCIO, FBuscaHR (de INT/VARCHAR a DATETIME)
- ✅ **Auditoría completa de DateTime en todas las tablas** - 7 campos verificados en 4 tablas
- ✅ **Conversión de fechas implementada** - TODOS los DateTime convertidos de Access a MySQL
- ✅ **Datos recientes confirmados** - Última fecha: 2025-11-03 (55 liquidaciones)
- ✅ **Relaciones verificadas:** 3 relaciones principales con tipos compatibles
- ✅ **Consultas JOIN verificadas** entre Liquidaciones, Socios, Cobradores y TbComentariosSocios
- ✅ 10 tablas con **98,133 registros activos** (de 102,272 totales)

**Solución implementada para Socios:**
```python
# Problema: NUMSOCIO y NUMSOCIO+NOMSOCIO tienen duplicados
# Solución: DROP/CREATE en cada sync (full refresh)
FULL_REFRESH_TABLES = ['Socios']

# Filtros aplicados:
TABLE_FILTERS = {
    'Socios': {
        'BAJA': '1',      # Excluir dados de baja
        'COMSOCIO': 'CU'  # Solo con cupones
    }
}
```

**Resultado:**
- ✅ Socios: Siempre **902 registros exactos** (BAJA<>1 AND COMSOCIO='CU')
- ✅ Sin duplicados en MySQL
- ✅ Performance: ~1 segundo para recrear tabla (menos registros que antes)
- ✅ Reducción: 82.1% menos datos (de 5,041 a 902)
- ⚠️ Trade-off: Se pierde historial de updated_at (aceptable)

**Testing Completado (20 Nov 2025):**
- ✅ clean_all_tables.py → sync_ALL.py → sync_INCREMENTAL.py ejecutado 7 veces exitosamente
- ✅ sync_INCREMENTAL.py muestra 0 cambios en 9 tablas (idempotencia 100% verificada)
- ✅ Socios hace full refresh correctamente (902 registros exactos)
- ✅ **VALIDACIÓN COMPLETA:** 47+ campos críticos verificados en 5 tablas principales
- ✅ **Campos corregidos en Cobradores:** NOMCOB, DOMCOB, SUBSOCIO, DESZONA, COBLIQUIDA
- ✅ **Campos corregidos en Socios (9 campos DateTime totales):** F1CSOCIO, FBuscaHR, ALTSOCIO, BAJAFECHA
- ✅ **Campos corregidos en Liquidaciones (7 campos):** ESTLIQUIDA, PERLIQUIDA, PERLIQUIDANRO, OBSLIQUIDA, PAGLIQUIDA, COMLIQUIDA, FECLIQUIDA
- ✅ **Conversión de fechas validada en 4 tablas (7 campos DateTime totales):**
  - Cobradores.ALTCOB: 26 registros (2006-04-10)
  - Socios: ALTSOCIO, F1CSOCIO, BAJAFECHA, FBuscaHR - 902 registros (2025-11-05, 2025-12-01)
  - Liquidaciones: FECLIQUIDA, PERLIQUIDANRO - 88,460 registros (2022-01-27 a 2025-11-03)
  - TbComentariosSocios.FechaCommet: 8,287 registros (2011-06-21)
- ✅ **Datos recientes verificados:** Fechas desde 2022 hasta 2025-11-03 (55 liquidaciones)
- ✅ **3 Relaciones verificadas:** Socios↔Liquidaciones, Cobradores↔Liquidaciones, TbComentariosSocios↔Socios
- ✅ Consultas JOIN validadas con tipos compatibles
- ✅ Performance verificada: 98,133 registros en ~40s (sync_ALL), ~10s (sync_INCREMENTAL)

**Validación Exhaustiva de Tipos:**
```
Cobradores     (10 campos): INT ✅ VARCHAR ✅ DECIMAL ✅ DATETIME ✅
  └─ ALTCOB: DATETIME (26 registros desde 2006)
Socios         (13 campos): INT ✅ VARCHAR ✅ DECIMAL ✅ DATETIME (4) ✅
  └─ ALTSOCIO: DATETIME (902 registros - 2025-11-05)
  └─ F1CSOCIO: DATETIME (902 registros - 2025-12-01) ← RECIÉN CORREGIDO
  └─ BAJAFECHA: DATETIME (mayormente NULL)
  └─ FBuscaHR: DATETIME (mayormente NULL) ← RECIÉN CORREGIDO
Liquidaciones  (17 campos): INT ✅ VARCHAR ✅ DECIMAL ✅ DATETIME (2) ✅
  └─ Especial: ESTLIQUIDA (VARCHAR - "CA", "DE", "AD", "BO")
  └─ Especial: PERLIQUIDA (VARCHAR - "Febrero /2022", etc.)
  └─ Especial: FECLIQUIDA (DATETIME - 88,460 registros convertidos)
  └─ Especial: PERLIQUIDANRO (DATETIME - convertida correctamente)
TbComentariosSocios (4 campos): INT ✅ VARCHAR ✅ DATETIME ✅
  └─ FechaCommet: DATETIME (8,287 registros desde 2011)
TblZonas        (2 campos): INT ✅ VARCHAR ✅
TblPromotores   (3 campos): INT ✅ VARCHAR ✅
```

**Status:** 🚀 **SISTEMA LISTO PARA PRODUCCIÓN**

**Próximos pasos sugeridos:** 
1. [ ] Automatizar con cron para sincronización diaria/horaria
2. [ ] Implementar logs a archivo para monitoreo
3. [ ] Considerar implementar soft delete en el futuro
4. [ ] Alertas por email en caso de errores
