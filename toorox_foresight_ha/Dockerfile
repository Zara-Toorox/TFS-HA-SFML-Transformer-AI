ARG BUILD_FROM

FROM python:3.14.2-slim-bookworm AS python-stage

FROM $BUILD_FROM

ENV LANG=C.UTF-8 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app \
    PATH=/usr/local/bin:$PATH

COPY --from=python-stage /usr/local /usr/local

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    openssl \
    curl \
    ca-certificates \
    libsqlite3-0 \
    libssl3 \
    libffi8 \
    libbz2-1.0 \
    liblzma5 \
    libncursesw6 \
    libreadline8 \
    libuuid1 \
    zlib1g \
    && rm -rf /var/lib/apt/lists/* \
    && ldconfig

WORKDIR /app

COPY requirements.txt .

RUN pip3 install --break-system-packages \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    torch numpy

RUN pip3 install --break-system-packages -r requirements.txt

COPY toorox_foresight/ ./toorox_foresight/
COPY scripts/ ./scripts/
COPY seed/ ./seed/
COPY pyarmor_runtime_009810/ ./pyarmor_runtime_009810/
COPY run.sh /run.sh
RUN chmod +x /run.sh

ENV FORESIGHT_DATA_DIR=/data \
    SFML_DB_PATH=/config/solar_forecast_ml/solar_forecast.db \
    API_HOST=0.0.0.0 \
    API_PORT=8780

EXPOSE 8780

CMD ["/run.sh"]
