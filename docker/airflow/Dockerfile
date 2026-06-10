FROM apache/airflow:2.10.4-python3.11

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        # --- Dependencias del sistema para GIS ---
        gdal-bin \
        libgdal-dev \
        libgeos-dev \
        libproj-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Configurar variables de entorno para que pip encuentre GDAL correctamente
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

USER airflow

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt \
    && pip install --no-cache-dir "SQLAlchemy>=1.4.36,<2.0"