#!/usr/bin/env bash
# Build a CPU-native kickmix wheel (AVX2 / AVX-512 SIMD paths enabled) into a separate venv.
#
# Why: the PyPI kickmix 1.0.0 wheel is compiled with `-mno-avx`, so the simulator runs on its
# 128-bit SSE path. The source already has b256_avx / b512_avx code; `-march=native` turns it on.
#
# Use the native build for FAST SCREENING only. Before you trust or submit anything, re-run the
# official verifier with the official PyPI wheel (the leaderboard uses that one).
#
# Usage: [MARCH=native|x86-64-v3|x86-64-v4] [NO_INSTALL=1] tools/build_native_kickmix.sh [QUALTRAN_DIR]
#   MARCH=native     fastest on THIS machine only (default; installs into .venv-native)
#   MARCH=x86-64-v3  portable AVX2 build: runs on any CPU from ~2015 on (Kaggle, Colab, GitHub Actions)
#   MARCH=x86-64-v4  portable AVX-512 build: needs avx512f/bw/cd/dq/vl (check /proc/cpuinfo)
#   Wheels land in .build/kickmix-native/dist/ tagged 1.0.0+<march>; tools/install_kickmix.py picks one.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="${ROOT}/.build/kickmix-native"
VENV="${ROOT}/.venv-native"
SRC="${1:-}"
MARCH="${MARCH:-native}"
TAG="${MARCH//[-.]/}"

mkdir -p "${WORK}"
if [[ -z "${SRC}" ]]; then
  if [[ ! -d "${WORK}/Qualtran" ]]; then
    git clone --depth 1 --filter=blob:none --sparse https://github.com/quantumlib/Qualtran "${WORK}/Qualtran"
    git -C "${WORK}/Qualtran" sparse-checkout set kickmix
  fi
  SRC="${WORK}/Qualtran"
fi

rm -rf "${WORK}/kickmix"
cp -r "${SRC}/kickmix" "${WORK}/kickmix"
cd "${WORK}/kickmix"
# Enable native SIMD; tag the version so the two builds are never confused.
sed -i "s/common_compile_args.append('-mno-avx')/common_compile_args.append('-march=${MARCH}')/" setup.py
sed -i "s/__version__ = '0.1.dev0'/__version__ = '1.0.0+${TAG}'/" setup.py
grep -q "march=${MARCH}" setup.py

[[ -d "${VENV}" ]] || python3 -m venv "${VENV}"
"${VENV}/bin/pip" install -q --upgrade pip wheel setuptools "pybind11==2.12.0" numpy
NPY_NUM_BUILD_JOBS="$(nproc)" MAX_JOBS="$(nproc)" "${VENV}/bin/pip" wheel -q --no-build-isolation -w "${WORK}/dist" .
[[ -n "${NO_INSTALL:-}" ]] && { ls -la "${WORK}"/dist/; exit 0; }
"${VENV}/bin/pip" install -q --force-reinstall --no-deps "${WORK}"/dist/kickmix-1.0.0+${TAG}-*.whl
"${VENV}/bin/python" -c "import kickmix; print('native kickmix installed:', kickmix.__file__)"
echo "Run verifiers with: ${VENV}/bin/python data/verifiers/..."
