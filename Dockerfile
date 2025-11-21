# Imagen base Python (bookworm tiene mdb-tools disponible)
FROM python:3.11-bookworm

# Instalar mdb-tools y git-lfs
RUN apt-get update && apt-get install -y \
    mdbtools \
    git \
    git-lfs \
    && rm -rf /var/lib/apt/lists/* \
    && git lfs install

# Directorio de trabajo
WORKDIR /app

# Copiar todo el código
COPY . .

# Descargar archivo LFS desde GitHub (repo público)
RUN cd /app && git init && \
    git remote add origin https://github.com/nahuelalejandrogomez/presencia-etl.git && \
    git lfs pull --include="data/Datos1.mdb" || echo "LFS pull skipped"

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# Exponer puerto
EXPOSE 8000

# Comando para ejecutar el servidor
CMD ["python", "server.py"]
