# 📊 Sistema de Sincronización Access → MySQL

## 🎯 Scripts Disponibles

### 1. `sync_ALL.py` - Sincronización COMPLETA
**Uso:** Primera vez o cuando quieres recargar TODO desde cero

```bash
cd /Users/nahuel/Documents/Desarrollos/P_M_Cobranza/migration_project
venv_project/bin/python sync_ALL.py
```

**Qué hace:**
- ❌ Borra y recrea todas las tablas
- ✅ Inserta TODOS los registros
- ⏱️ Tiempo: ~65 segundos
- 📊 Total: 246,047 registros

**Logs detallados:**
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
   ✅ COMPLETADO: 88,460 registros en MySQL
```

---

### 2. `sync_INCREMENTAL.py` - Sincronización INTELIGENTE ⚡
**Uso:** Uso diario, cada vez que haya cambios

```bash
cd /Users/nahuel/Documents/Desarrollos/P_M_Cobranza/migration_project
venv_project/bin/python sync_INCREMENTAL.py
```

**Qué hace:**
- 🔍 Compara cada registro usando HASH
- ➕ Solo inserta registros NUEVOS
- 🔄 Solo actualiza registros MODIFICADOS
- ⏭️ Salta registros sin cambios
- ⏱️ Tiempo: ~5-10 segundos (si no hay cambios masivos)

**Cómo detecta cambios:**
1. Calcula hash (SHA-256) de TODOS los campos del registro
2. Compara con hash guardado en MySQL
3. Si son diferentes → UPDATE
4. Si son iguales → SKIP

**Logs detallados:**
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

## 📋 Tablas Sincronizadas

| Tabla | Registros | Descripción |
|-------|-----------|-------------|
| **PlaCobranzas** | 143,775 | Planillas de cobranzas |
| **Liquidaciones** | 88,460 | Liquidaciones |
| **TbComentariosSocios** | 8,287 | Comentarios |
| **Socios** | 5,041 | Socios |
| **TblZonas** | 344 | Zonas |
| Cobradores | 26 | Cobradores |
| TblPromotores | 28 | Promotores |
| TblObras | 57 | Obras sociales |
| TblPlanes | 24 | Planes |
| TblIva | 4 | Categorías IVA |
| TblFPagos | 1 | Formas de pago |

---

## 🔧 Otros Scripts Útiles

### `demo_incremental.py` - Ver cómo funciona el hash
```bash
venv_project/bin/python demo_incremental.py
```

### `drop_unused_tables.py` - Limpiar tablas innecesarias
```bash
venv_project/bin/python drop_unused_tables.py
```

---

## 📝 Ejemplo de Uso Típico

### Primera vez (setup inicial):
```bash
# 1. Carga completa inicial
venv_project/bin/python sync_ALL.py
```

### Uso diario (actualizaciones):
```bash
# 2. Sincronizar solo cambios (RÁPIDO)
venv_project/bin/python sync_INCREMENTAL.py
```

### Si algo sale mal (resetear):
```bash
# 3. Volver a cargar todo desde cero
venv_project/bin/python sync_ALL.py
```

---

## ⚡ Ventajas del Sistema

### sync_ALL.py:
- ✅ Garantiza datos limpios
- ✅ Recrea esquema automáticamente
- ⚠️ Borra TODO (usar con cuidado)
- ⏱️ Lento pero seguro

### sync_INCREMENTAL.py:
- ✅ Súper rápido (solo procesa cambios)
- ✅ Detecta cualquier modificación
- ✅ No borra datos
- ✅ Mantiene historial (updated_at)
- ✅ Puedes ejecutarlo cada 5 minutos
- ✅ Ideal para automatizar

---

## 🔐 Configuración

Los scripts usan el archivo `.env`:
```bash
COBRANZA_DB_HOST=srv1781.hstgr.io
COBRANZA_DB_NAME=u596151945_cobranza
COBRANZA_DB_USER=u596151945_cobranza
COBRANZA_DB_PASSWORD=cobranzaPresencia1*
COBRANZA_ACCESS_PATH=/Users/nahuel/Documents/Desarrollos/P_M_Cobranza/BBDD/Datos1.mdb
```

---

## 📊 Estadísticas de Performance

| Script | Tiempo | Registros/seg |
|--------|--------|---------------|
| sync_ALL.py | ~65 seg | ~3,785 reg/s |
| sync_INCREMENTAL.py (sin cambios) | ~8 seg | Validación rápida |
| sync_INCREMENTAL.py (con cambios) | Variable | Depende cantidad de cambios |

---

## 🎓 Cómo Funciona el HASH

```python
# Ejemplo simplificado:
registro = {
    'NUMLIQUIDA': 2024,
    'FECLIQUIDA': '2022-01-27',
    'MONTO': 1500.00
}

# 1. Concatena todos los valores en orden
contenido = "2024|2022-01-27|1500.00"

# 2. Calcula SHA-256
hash = "a3f4b2c8d1e9..." (64 caracteres)

# 3. Guarda el hash en MySQL
# Si cambias CUALQUIER valor, el hash será diferente
```

---

## 🚨 Importante

- **sync_ALL.py**: Úsalo solo cuando necesites resetear
- **sync_INCREMENTAL.py**: Para uso diario
- Los registros tienen `updated_at` que muestra última modificación
- Todos los registros tienen `id` auto-increment como PK real
- Las PK originales (NUMLIQUIDA, etc.) se mantienen pero como campos normales

---

## 📞 Resumen Rápido

**¿Primera vez?** → `sync_ALL.py`  
**¿Actualizar datos?** → `sync_INCREMENTAL.py`  
**¿Ver estadísticas?** → `demo_incremental.py`  
**¿Limpiar?** → `drop_unused_tables.py`
