#!/usr/bin/env python3
"""Install the fastest kickmix wheel this CPU can run (for local screening only).

Order: x86-64-v4 (AVX-512) -> x86-64-v3 (AVX2) -> official PyPI kickmix (SSE, what the leaderboard uses).
All builds give bit-identical verifier results on the invsqrt frontier circuit (see PLAN.md); still, re-run
the final candidate with the official wheel before submitting.

Usage (Kaggle / Colab / local):
  python tools/install_kickmix.py --wheels DIR [--target DIR] [--official]
    --wheels   folder holding kickmix-1.0.0+x8664v4-*.whl / +x8664v3-*.whl (our Kaggle dataset ships them)
    --target   install into this folder instead of site-packages (then put it first on sys.path)
    --official skip the fast builds and install PyPI kickmix
Prints the chosen build. Exit code 0 on success.
"""
import argparse, glob, platform, subprocess, sys
from pathlib import Path

V4 = {'avx512f', 'avx512bw', 'avx512cd', 'avx512dq', 'avx512vl'}
V3 = {'avx2', 'fma', 'bmi1', 'bmi2', 'movbe'}


def cpu_flags():
    try:
        for line in open('/proc/cpuinfo'):
            if line.startswith('flags'):
                return set(line.split(':', 1)[1].split())
    except OSError:
        pass
    return set()


def pick(wheels_dir):
    if platform.machine().lower() not in ('x86_64', 'amd64'):
        return None, 'official (non-x86 CPU)'
    flags = cpu_flags()
    py = f'cp{sys.version_info.major}{sys.version_info.minor}'
    for tag, need in (('x8664v4', V4), ('x8664v3', V3)):
        if need <= flags:
            found = sorted(glob.glob(str(Path(wheels_dir) / f'kickmix-1.0.0+{tag}-{py}-*.whl')))
            if found:
                return found[-1], tag
    return None, f'official (no matching fast wheel for {py})'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--wheels', default=str(Path(__file__).resolve().parent.parent / '.build/kickmix-native/dist'))
    ap.add_argument('--target')
    ap.add_argument('--official', action='store_true')
    a = ap.parse_args()
    wheel, label = (None, 'official (requested)') if a.official else pick(a.wheels)
    cmd = [sys.executable, '-m', 'pip', 'install', '-q', '--no-deps', '--force-reinstall']
    if a.target:
        cmd += ['--target', a.target]
    cmd += [wheel or 'kickmix==1.0.0']
    subprocess.run(cmd, check=True)
    print(f'kickmix build: {label}' + (f' ({Path(wheel).name})' if wheel else ''))


if __name__ == '__main__':
    main()
