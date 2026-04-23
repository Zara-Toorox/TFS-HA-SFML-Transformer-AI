#!/bin/sh
set -e

mkdir -p "${TFS_STATE_DIR}"

CONFIG_FILE="/data/options.json"
if [ -f "${CONFIG_FILE}" ]; then
    export TFS_OPTIONS_JSON="${CONFIG_FILE}"
fi

if [ -z "${TFS_MODEL_KEY_FILE:-}" ] && [ -z "${TFS_MODEL_KEY_B64:-}" ]; then
    DEFAULT_MODEL_KEY_FILE="${TFS_STATE_DIR}/model-key.b64"
    if [ -f "${DEFAULT_MODEL_KEY_FILE}" ]; then
        export TFS_MODEL_KEY_FILE="${DEFAULT_MODEL_KEY_FILE}"
    fi
fi

if [ -z "${TFS_MODEL_KEY_FILE:-}" ] && [ -z "${TFS_MODEL_KEY_B64:-}" ]; then
    if find "${TFS_MODEL_DIR}/base" -maxdepth 1 -type f -name '*.safetensors.enc' | grep -q .; then
        echo "Encrypted base model found, but no model key is configured." >&2
        echo "Expected key file: ${TFS_STATE_DIR}/model-key.b64" >&2
        exit 1
    fi
fi

exec python -u /app/scripts/serve.py
