# Imagen base Python (bookworm tiene mdb-tools disponible)
FROM python:3.11-bookworm

# Instalar mdb-tools y git-lfs
RUN apt-get update && apt-get install -y \
    mdbtools \
    git \
    git-lfs \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && git lfs install

# Directorio de trabajo
WORKDIR /app

# Copiar todo el código (excepto el archivo LFS que es solo puntero)
COPY . .

# Descargar el archivo Access directamente desde GitHub LFS
# Primero obtenemos el SHA del archivo desde el puntero
RUN LFS_SHA=$(grep 'oid sha256:' /app/data/Datos1.mdb | cut -d: -f2) && \
    echo "Descargando archivo LFS con SHA: $LFS_SHA" && \
    curl -L -o /app/data/Datos1.mdb \
    "https://github.com/nahuelalejandrogomez/presencia-etl.git/info/lfs/objects/batch" \
    -H "Accept: application/vnd.git-lfs+json" \
    -H "Content-Type: application/vnd.git-lfs+json" \
    -d "{\"operation\":\"download\",\"objects\":[{\"oid\":\"$LFS_SHA\",\"size\":105943040}]}" \
    || echo "Curl directo fallido, intentando git clone..."

# Si curl falló, clonar el repo completo
RUN if [ $(stat -c%s /app/data/Datos1.mdb) -lt 1000 ]; then \
    echo "Archivo aún es puntero, clonando repo completo..." && \
    rm -rf /tmp/repo && \
    GIT_LFS_SKIP_SMUDGE=0 git clone https://github.com/nahuelalejandrogomez/presencia-etl.git /tmp/repo && \
    cp /tmp/repo/data/Datos1.mdb /app/data/Datos1.mdb && \
    rm -rf /tmp/repo; \
    fi

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# Exponer puerto
EXPOSE 8000

# Comando para ejecutar el servidor
CMD ["python", "server.py"]
