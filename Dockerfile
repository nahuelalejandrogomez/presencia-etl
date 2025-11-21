# Imagen base Python
FROM python:3.11-slim

# Instalar mdb-tools (necesario para leer archivos Access .mdb)
RUN apt-get update && apt-get install -y \
    mdb-tools \
    && rm -rf /var/lib/apt/lists/*

# Directorio de trabajo
WORKDIR /app

# Copiar requirements primero (para cachear dependencias)
COPY requirements.txt .

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .

# Exponer puerto (Railway usa la variable PORT)
EXPOSE 8000

# Comando para ejecutar el servidor
CMD ["python", "server.py"]
