ARG BUILD_FROM
ARG APP_SOURCE_ROOT=.

FROM python:3.12-slim-bookworm AS python-stage

ARG APP_SOURCE_ROOT=.
FROM $BUILD_FROM

ENV LANG=C.UTF-8 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app \
    PATH=/usr/local/bin:$PATH \
    TFS_STATE_DIR=/config/toorox_foresight_ha \
    TFS_MODEL_DIR=/app/models \
    OMP_NUM_THREADS=4 \
    MKL_NUM_THREADS=4

COPY --from=python-stage /usr/local /usr/local

RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
        libopenblas0 \
        liblapack3 \
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
        tini \
    && rm -rf /var/lib/apt/lists/* \
    && ldconfig

WORKDIR /app

COPY ${APP_SOURCE_ROOT}/requirements.txt /app/requirements.txt

RUN pip3 install --break-system-packages \
        --extra-index-url https://download.pytorch.org/whl/cpu \
        -r /app/requirements.txt

COPY ${APP_SOURCE_ROOT}/toorox_foresight /app/toorox_foresight
COPY ${APP_SOURCE_ROOT}/scripts /app/scripts
COPY ${APP_SOURCE_ROOT}/models /app/models
COPY ${APP_SOURCE_ROOT}/run.sh /app/run.sh
COPY ${APP_SOURCE_ROOT}/pyarmor_runtime_009810 /app/pyarmor_runtime_009810
RUN chmod +x /app/run.sh

EXPOSE 8780

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/app/run.sh"]
