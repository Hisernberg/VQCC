#!/usr/bin/env bash
# Package the toolkit as a PRIVATE Kaggle dataset: <user>/vqcc-toolkit
#
# Contents: loop/ (verify harness, agent driver, seeds, prompts), tools/, catalog/, PLAN.md,
#           wheels/ (kickmix 1.0.0 built for x86-64-v3 = AVX2 and x86-64-v4 = AVX-512, cp313).
# No tokens, no competition data, no third-party circuits (attach those datasets separately).
#
# Usage: KAGGLE_API_TOKEN=... tools/make_kaggle_dataset.sh [kaggle_user] ["version message"]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
USER_SLUG="${1:-kragglenote2forwork}"
MSG="${2:-update}"
OUT="${ROOT}/.build/kaggle_dataset"

rm -rf "${OUT:?}"
mkdir -p "${OUT}/wheels"
cp -r "${ROOT}/loop" "${ROOT}/tools" "${ROOT}/catalog" "${ROOT}/PLAN.md" "${OUT}/"
cp "${ROOT}"/.build/kickmix-native/dist/kickmix-1.0.0+x8664v[34]-*.whl "${OUT}/wheels/"
cp "${ROOT}/.build/kickmix-native/kickmix/LICENSE" "${OUT}/wheels/KICKMIX_LICENSE" 2>/dev/null || true
find "${OUT}" -name __pycache__ -prune -exec rm -r {} +
# Refuse to publish anything that looks like a credential.
if grep -rIlE --exclude=make_kaggle_dataset.sh 'KGAT_[0-9a-f]{8}|ghp_[A-Za-z0-9]{20}|hf_[A-Za-z0-9]{20}|sk-[A-Za-z0-9]{20}|nvapi-' "${OUT}"; then
  echo "credential-like string found above; aborting" >&2; exit 1
fi
cat > "${OUT}/dataset-metadata.json" <<EOF
{"title": "VQCC toolkit", "id": "${USER_SLUG}/vqcc-toolkit", "licenses": [{"name": "Apache 2.0"}],
 "subtitle": "Verify harness, agent driver, drift tracker and AVX2/AVX-512 kickmix wheels"}
EOF
if kaggle datasets status "${USER_SLUG}/vqcc-toolkit" >/dev/null 2>&1; then
  kaggle datasets version -p "${OUT}" -m "${MSG}" --dir-mode zip
else
  kaggle datasets create -p "${OUT}" --dir-mode zip   # private by default
fi
