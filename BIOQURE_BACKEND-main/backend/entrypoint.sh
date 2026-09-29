#!/usr/bin/env sh
set -eu

seed_root="${GENEZAP_PUBLIC_DATASET_SEED_ROOT:-/app/bootstrap_data/datasets}"
target_root="${GENEZAP_DATASETS_ROOT:-/data/datasets}"
seed_pool="$seed_root/pools/default-public-pool"
target_pool="$target_root/pools/default-public-pool"

if [ ! -d "$target_pool/files" ] && [ -d "$seed_pool/files" ]; then
    mkdir -p "$target_root/pools"
    cp -a "$seed_pool" "$target_root/pools/"
fi

bash /app/backend/download_models.sh
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"