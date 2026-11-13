# vqcc-runner: free Kaggle CPU worker for the VQCC loop.
#
# 1. Finds the attached inputs (competition data, our vqcc-toolkit dataset, a frontier circuit dataset).
# 2. Installs the fastest kickmix wheel this CPU supports and benchmarks it against the official build.
# 3. Runs the agent driver. Provider/model/key come from Kaggle Secrets:
#      VQCC_PROVIDER (nim|groq|cerebras|openrouter|gemini|local), VQCC_MODEL, and that provider's key
#      (NVIDIA_API_KEY, GROQ_API_KEY, ...). With no secrets it does a 1-iteration dry run.
# 4. Leaves runs/ and results.jsonl in /kaggle/working (download them or chain them into the next run).
import glob, json, os, shutil, subprocess, sys, time
from pathlib import Path

W = Path('/kaggle/working/vqcc')


def find(pattern):
    hits = sorted(glob.glob('/kaggle/input/**/' + pattern, recursive=True))
    return Path(hits[0]) if hits else None


def sh(cmd, **kw):
    print('$', cmd, flush=True)
    return subprocess.run(cmd, shell=True, text=True, **kw)


toolkit = find('loop/verify.py')
if toolkit is None:  # dataset uploaded in zip mode and not extracted
    z = find('loop.zip')
    for zz in z.parent.glob('*.zip'):
        shutil.unpack_archive(zz, '/kaggle/working/_tk/' + zz.stem)
    toolkit = Path('/kaggle/working/_tk/loop/loop/verify.py')
tk = toolkit.parent.parent
verifier = find('verifiers/invsqrt/verify_submission_invsqrt.py')
comp = verifier.parents[2]
frontier = find('invsqrt.kmb')
print('toolkit:', tk, '\ncompetition:', comp, '\nfrontier invsqrt:', frontier)

shutil.copytree(tk, W, dirs_exist_ok=True, ignore=shutil.ignore_patterns('wheels'))
(W / 'data').mkdir(exist_ok=True)
for name in ('verifiers', 'sample_submission'):
    if not (W / 'data' / name).exists():
        os.symlink(comp / name, W / 'data' / name)
(W / 'frontier').mkdir(exist_ok=True)
for f in frontier.parent.iterdir():
    if not (W / 'frontier' / f.name).exists():
        os.symlink(f, W / 'frontier' / f.name)

# --- 1. CPU and kickmix builds -------------------------------------------------------------------
sh('nproc; lscpu | grep -E "Model name|^CPU\\(s\\)"; grep -o -w -E "avx2|avx512f|avx512bw|avx512vl" /proc/cpuinfo | sort | uniq -c')
fast = '/kaggle/working/km_fast'
sh(f'{sys.executable} {W}/tools/install_kickmix.py --wheels {tk}/wheels --target {fast}', check=True)
official = str(comp / 'kickmix')  # the exact kickmix.so the leaderboard uses


def timed_verify(label, pypath):
    t = time.time()
    p = sh(f'PYTHONPATH={pypath} {sys.executable} {W}/data/verifiers/invsqrt/verify_submission_invsqrt.py '
           f'{W}/frontier/invsqrt.kmb', capture_output=True)
    res = json.loads(p.stdout[p.stdout.index('{'):])
    print(f'{label}: {res["status"]} score={res.get("score")} worst={res.get("worst_error_over_tolerance")} '
          f'time={time.time() - t:.0f}s', flush=True)
    return res


r_off = timed_verify('official kickmix', official)
r_fast = timed_verify('fast kickmix', fast)
print('IDENTICAL RESULTS' if (r_off.get('score'), r_off.get('worst_error_over_tolerance')) ==
      (r_fast.get('score'), r_fast.get('worst_error_over_tolerance')) else 'RESULTS DIFFER: use the official build')

# --- 2. Agent driver ---------------------------------------------------------------------------
env = {}
try:
    from kaggle_secrets import UserSecretsClient
    sec = UserSecretsClient()
    for k in ('VQCC_PROVIDER', 'VQCC_MODEL', 'VQCC_ITERS', 'NVIDIA_API_KEY', 'GROQ_API_KEY', 'CEREBRAS_API_KEY',
              'OPENROUTER_API_KEY', 'GEMINI_API_KEY'):
        try:
            env[k] = sec.get_secret(k)
        except Exception:
            pass
except ImportError:
    pass
provider = env.get('VQCC_PROVIDER', 'dry')
iters = env.get('VQCC_ITERS', '1' if provider == 'dry' else '40')
os.environ.update({k: v for k, v in env.items() if v})
os.environ['PYTHONPATH'] = fast  # screening uses the fast build; verify the final pick with the official one
sh(f'cd {W} && {sys.executable} loop/driver.py --task invsqrt --seed loop/seeds/invsqrt_peephole.py '
   f'--provider {provider} --model "{env.get("VQCC_MODEL", "")}" --iters {iters}')
sh(f'cd {W} && tail -n 5 runs/invsqrt/journal.jsonl; cat runs/invsqrt/best.json 2>/dev/null; true')
