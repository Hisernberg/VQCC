#!/usr/bin/env python3
"""Agent driver: LLM proposes a generator change -> build -> official verifier -> keep or discard -> journal.

Works with any OpenAI-compatible chat endpoint, so it runs on FREE providers or a local model:
  --provider nim         https://integrate.api.nvidia.com/v1   (key: NVIDIA_API_KEY)
  --provider groq        https://api.groq.com/openai/v1         (key: GROQ_API_KEY)
  --provider cerebras    https://api.cerebras.ai/v1             (key: CEREBRAS_API_KEY)
  --provider openrouter  https://openrouter.ai/api/v1           (key: OPENROUTER_API_KEY, use ':free' models)
  --provider gemini      https://generativelanguage.googleapis.com/v1beta/openai (key: GEMINI_API_KEY)
  --provider local       http://127.0.0.1:8000/v1               (llama.cpp / vLLM / Ollama on a Kaggle GPU)
  --provider dry         no LLM: re-runs the seed unchanged (tests the pipeline)

On Kaggle, store keys as notebook Secrets and export them as env vars. Never commit keys.

Usage:
  python loop/driver.py --task invsqrt --seed loop/seeds/invsqrt_peephole.py \
      --provider nim --model deepseek-ai/deepseek-v4.1-flash --iters 50

Files: runs/<task>/journal.jsonl (every attempt), runs/<task>/best_gen.py + best.kmb (current best),
       runs/<task>/attempts/NNNN/ (generator, output, logs).
Safety: LLM-written code runs in a subprocess with `python -I`, a timeout, and its own folder. Run the
driver inside a disposable environment (a Kaggle notebook is ideal).
"""
import argparse, json, os, re, shutil, subprocess, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROVIDERS = {
    'nim': ('https://integrate.api.nvidia.com/v1', 'NVIDIA_API_KEY'),
    'groq': ('https://api.groq.com/openai/v1', 'GROQ_API_KEY'),
    'cerebras': ('https://api.cerebras.ai/v1', 'CEREBRAS_API_KEY'),
    'openrouter': ('https://openrouter.ai/api/v1', 'OPENROUTER_API_KEY'),
    'gemini': ('https://generativelanguage.googleapis.com/v1beta/openai', 'GEMINI_API_KEY'),
    'local': ('http://127.0.0.1:8000/v1', None),
}


def chat(provider, model, messages, temperature=0.7, retries=4):
    base, key_env = PROVIDERS[provider]
    base = os.environ.get('LLM_BASE_URL', base)
    headers = {'Content-Type': 'application/json'}
    if key_env:
        headers['Authorization'] = 'Bearer ' + os.environ[key_env]
    body = json.dumps({'model': model, 'messages': messages, 'temperature': temperature}).encode()
    for i in range(retries):
        try:
            req = urllib.request.Request(base.rstrip('/') + '/chat/completions', body, headers)
            with urllib.request.urlopen(req, timeout=600) as r:
                return json.load(r)['choices'][0]['message']['content']
        except Exception as e:  # rate limits on free tiers are normal: back off
            wait = 2 ** (i + 3)
            print(f'LLM call failed ({e}); retry in {wait}s', file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError('LLM unavailable')


def verify(task, kmb, quick):
    cmd = [sys.executable, str(ROOT / 'loop/verify.py'), task, str(kmb), '--note', 'driver']
    if quick:
        cmd.append('--quick')
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    try:
        return json.loads(out[out.index('{'):])
    except ValueError:
        return {'status': 'FAIL', 'error': out[-500:]}


def run_generator(gen, out_kmb, timeout):
    env = dict(os.environ, VQCC_ROOT=str(ROOT))
    p = subprocess.run([sys.executable, '-I', str(gen), str(out_kmb)], capture_output=True, text=True,
                       timeout=timeout, env=env, cwd=gen.parent)
    return p.returncode, p.stdout[-2000:], p.stderr[-2000:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--task', default='invsqrt', choices=['invsqrt', 'dqi'])
    ap.add_argument('--seed', required=True, help='seed generator (python file following the contract)')
    ap.add_argument('--provider', default='dry', choices=list(PROVIDERS) + ['dry'])
    ap.add_argument('--model', default='')
    ap.add_argument('--iters', type=int, default=10)
    ap.add_argument('--gen-timeout', type=int, default=900)
    ap.add_argument('--journal-tail', type=int, default=12)
    ap.add_argument('--min-gain', type=float, default=1e-4,
                    help='relative improvement needed to replace the best; re-seeded HMR outcomes alone move '
                         'the invsqrt cost by ~1e-6, so smaller "gains" are noise')
    a = ap.parse_args()

    run = ROOT / 'runs' / a.task
    (run / 'attempts').mkdir(parents=True, exist_ok=True)
    journal = run / 'journal.jsonl'
    best_gen = run / 'best_gen.py'
    best_meta = run / 'best.json'
    if not best_gen.exists():
        shutil.copy(a.seed, best_gen)
    best = json.loads(best_meta.read_text()) if best_meta.exists() else {'score': float('inf')}
    brief = (ROOT / 'loop/prompts' / f'{a.task}.md').read_text()
    prices = (ROOT / 'catalog/components.csv').read_text()[:6000] if (ROOT / 'catalog/components.csv').exists() else ''

    start = len(journal.read_text().splitlines()) if journal.exists() else 0
    for it in range(start, start + a.iters):
        adir = run / 'attempts' / f'{it:04d}'
        adir.mkdir(exist_ok=True)
        gen = adir / 'gen.py'
        hyp = 'dry run: seed unchanged'
        if a.provider == 'dry':
            shutil.copy(best_gen, gen)
        else:
            tail = journal.read_text().splitlines()[-a.journal_tail:] if journal.exists() else []
            msgs = [
                {'role': 'system', 'content': brief},
                {'role': 'user', 'content':
                    f'Price list of kickmix building blocks (CSV):\n{prices}\n\n'
                    f'Recent attempts (JSON lines, newest last; do not repeat failures):\n' + '\n'.join(tail) +
                    f'\n\nCurrent best cost: {best["score"]}\nCurrent best generator:\n```python\n'
                    f'{best_gen.read_text()}\n```\nPropose ONE change.'},
            ]
            reply = chat(a.provider, a.model, msgs)
            (adir / 'reply.md').write_text(reply)
            m = re.search(r'```python\n(.*?)```', reply, re.S)
            h = re.search(r'HYPOTHESIS:\s*(.+)', reply)
            hyp = h.group(1).strip() if h else '(none given)'
            if not m:
                rec = {'it': it, 'hypothesis': hyp, 'status': 'NO_CODE'}
                journal.open('a').write(json.dumps(rec) + '\n')
                continue
            gen.write_text(m.group(1))

        rec = {'it': it, 'time': time.strftime('%H:%M:%S'), 'hypothesis': hyp}
        out = adir / 'out.kmb'
        try:
            rc, so, se = run_generator(gen, out, a.gen_timeout)
        except subprocess.TimeoutExpired:
            rc, so, se = -1, '', 'timeout'
        (adir / 'gen.log').write_text(so + '\n--- stderr ---\n' + se)
        if rc != 0 or not out.exists():
            rec.update(status='BUILD_FAIL', error=se[-300:])
        else:
            q = verify(a.task, out, quick=True)
            rec.update(quick=q.get('status'), quick_score=q.get('score'))
            if q.get('status') == 'PASS' and q.get('score', 1e300) < best['score'] * 1.0005:
                f = verify(a.task, out, quick=False)
                rec.update(status=f.get('status'), score=f.get('score'))
                if f.get('status') == 'PASS' and f['score'] < best['score'] * (1 - a.min_gain):
                    best = {'score': f['score'], 'it': it, 'hypothesis': hyp, 'sha256': f.get('sha256')}
                    shutil.copy(gen, best_gen)
                    shutil.copy(out, run / 'best.kmb')
                    best_meta.write_text(json.dumps(best))
                    rec['new_best'] = True
            else:
                rec['status'] = 'REJECT_QUICK' if q.get('status') == 'PASS' else 'FAIL'
                rec['error'] = str(q.get('error', ''))[:300]
            out.unlink(missing_ok=True)  # circuits are large; keep only the best
        journal.open('a').write(json.dumps(rec) + '\n')
        print(json.dumps(rec))


if __name__ == '__main__':
    main()
