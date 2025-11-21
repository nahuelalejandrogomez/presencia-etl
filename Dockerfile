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

# Clonar el repo con LFS
ARG REPO_URL=https://github.com/nahuelalejandrogomez/presencia-etl.git
RUN git clone --depth 1 ${REPO_URL} /tmp/repo \
    && cd /tmp/repo \
    && git lfs pull \
    && cp -r /tmp/repo/* /app/ \
    && rm -rf /tmp/repo

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# Exponer puerto (Railway usa la variable PORT)
EXPOSE 8000

# Comando para ejecutar el servidor
CMD ["python", "server.py"]
