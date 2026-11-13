#!/usr/bin/env python3
"""Frontier drifter: snapshot the public state of the competition and report what moved.

Each run writes snapshots/<UTC timestamp>/ with:
  leaderboard.csv   full public leaderboard
  kernels.json      public notebooks (by recency, score and votes)
  datasets.json     public datasets matching competition keywords
  topics.json       all discussion topics (with comment counts)
  REPORT.md         diff against the previous snapshot

Needs KAGGLE_API_TOKEN (or ~/.kaggle/kaggle.json) in the environment. Never commit the token.
Usage: python tools/drift.py [--me TEAM_NAME_OR_USER]
"""
import argparse, csv, glob, io, json, os, re, subprocess, sys, time, zipfile
from pathlib import Path

COMP = 'google-verifiable-quantum-circuit-compilation'
ROOT = Path(__file__).resolve().parent.parent
SNAP = ROOT / 'snapshots'
DATASET_QUERIES = ['vqcc', 'qcc', 'quantum circuit compilation', 'kickmix', 'dqi decoder', 'invsqrt']
SCORE_RE = re.compile(r'(?<![\d.])(2\d\.\d{2,6})(?![\d])')  # titles like "LB 27.11042"


def kaggle_csv(args):
    out = subprocess.run(['kaggle'] + args + ['--csv'], capture_output=True, text=True).stdout
    lines = [l for l in out.splitlines() if l and not l.startswith(('Warning', 'Next Page'))]
    return list(csv.DictReader(io.StringIO('\n'.join(lines)))) if lines else []


def fetch_leaderboard(dst):
    tmp = dst / '_lb'
    tmp.mkdir(exist_ok=True)
    subprocess.run(['kaggle', 'competitions', 'leaderboard', COMP, '-d', '-p', str(tmp), '-q'], capture_output=True)
    for z in tmp.glob('*.zip'):
        with zipfile.ZipFile(z) as f:
            name = [n for n in f.namelist() if n.endswith('.csv')][0]
            (dst / 'leaderboard.csv').write_bytes(f.read(name))
        z.unlink()
    tmp.rmdir()


def fetch_kernels():
    seen = {}
    for sort in ['dateRun', 'scoreDescending', 'voteCount']:
        for page in (1, 2):
            for k in kaggle_csv(['kernels', 'list', '--competition', COMP, '--sort-by', sort, '--page-size', '100', '-p', str(page)]):
                seen[k['ref']] = k
    for k in seen.values():
        m = SCORE_RE.findall(k.get('title', ''))
        k['title_score'] = max(map(float, m)) if m else None
    return seen


def fetch_datasets():
    seen = {}
    for q in DATASET_QUERIES:
        for d in kaggle_csv(['datasets', 'list', '-s', q, '--sort-by', 'updated']):
            seen[d['ref']] = d
    return seen


def fetch_topics():
    from kagglesdk import KaggleClient
    from kagglesdk.competitions.types.competition_api_service import ApiListCompetitionTopicsRequest
    client, topics, page = KaggleClient(), {}, 1
    while True:
        r = ApiListCompetitionTopicsRequest()
        r.competition_name, r.page = COMP, page
        resp = client.competitions.competition_api_client.list_competition_topics(r)
        for t in resp.topics:
            topics[str(t.id)] = {'title': t.title, 'author': t.author_name, 'votes': t.votes,
                                 'comments': t.comment_count, 'posted': str(t.post_date),
                                 'last_comment': str(t.last_comment_post_date),
                                 'url': 'https://www.kaggle.com' + (t.topic_url or '')}
        if not resp.topics or len(topics) >= (resp.total_count or 0):
            break
        page += 1
    return topics


def read_lb(path):
    with open(path, encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def report(cur, prev, me):
    lines = [f"# Drift report {cur.name}", '']
    lb = read_lb(cur / 'leaderboard.csv')
    lines += ['## Leaderboard', '', '| Rank | Team | Score | Δ since last |', '|---:|---|---:|---:|']
    old = {r['TeamId']: float(r['Score']) for r in read_lb(prev / 'leaderboard.csv')} if prev else {}
    for r in lb[:15]:
        d = float(r['Score']) - old.get(r['TeamId'], float(r['Score']))
        lines.append(f"| {r['Rank']} | {r['TeamName']} | {float(r['Score']):.5f} | {d:+.5f} |")
    scores = [float(r['Score']) for r in lb]
    lines += ['', 'Score at rank ' + ', '.join(f"{n}: {scores[n-1]:.3f}" for n in (10, 50, 100, 500) if n <= len(scores))]
    if me:
        mine = [r for r in lb if me.lower() in (r['TeamName'] + ' ' + r.get('TeamMemberUserNames', '')).lower()]
        for r in mine:
            lines.append(f"**You:** rank {r['Rank']}, score {float(r['Score']):.5f}")
    # Biggest plateaus = public notebooks everyone forked.
    from collections import Counter
    plat = Counter(round(s, 3) for s in scores).most_common(4)
    lines.append('Plateaus (forked public builds): ' + ', '.join(f"{s} × {n}" for s, n in plat))

    kern = json.loads((cur / 'kernels.json').read_text())
    okern = json.loads((prev / 'kernels.json').read_text()) if prev else {}
    best_pub = max((k for k in kern.values() if k['title_score']), key=lambda k: k['title_score'], default=None)
    lines += ['', '## Notebooks', '']
    if best_pub:
        lines.append(f"Highest score claimed in a public notebook title: **{best_pub['title_score']}**, "
                     f"[{best_pub['title']}](https://www.kaggle.com/code/{best_pub['ref']})")
    new = [k for r, k in kern.items() if r not in okern]
    upd = [k for r, k in kern.items() if r in okern and k['lastRunTime'] != okern[r]['lastRunTime']]
    for label, items in (('New', new), ('Updated', upd)):
        items = sorted(items, key=lambda k: (k['title_score'] or 0, int(k['totalVotes'] or 0)), reverse=True)[:15]
        if items:
            lines += ['', f'**{label}:**']
            lines += [f"- {k['title_score'] or ''} [{k['title']}](https://www.kaggle.com/code/{k['ref']}) "
                      f"by {k['author']}, {k['totalVotes']} votes" for k in items]

    ds = json.loads((cur / 'datasets.json').read_text())
    ods = json.loads((prev / 'datasets.json').read_text()) if prev else {}
    newds = [d for r, d in ds.items() if r not in ods or d.get('lastUpdated') != ods[r].get('lastUpdated')]
    if newds:
        lines += ['', '## New or updated datasets', '']
        lines += [f"- [{d['title']}](https://www.kaggle.com/datasets/{d['ref']}) updated {d['lastUpdated'][:16]}, "
                  f"{d['downloadCount']} downloads" for d in newds[:15]]

    tp = json.loads((cur / 'topics.json').read_text())
    otp = json.loads((prev / 'topics.json').read_text()) if prev else {}
    act = [(i, t) for i, t in tp.items() if i not in otp or t['comments'] != otp[i]['comments']]
    if act:
        lines += ['', '## Discussion activity', '']
        for i, t in sorted(act, key=lambda x: x[1]['last_comment'], reverse=True)[:20]:
            tag = 'NEW' if i not in otp else f"+{t['comments'] - otp[i]['comments']} comments"
            lines.append(f"- [{t['title']}]({t['url']}) ({tag}, {t['votes']} votes)")
    return '\n'.join(lines) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--me', default=os.environ.get('VQCC_ME', ''))
    ap.add_argument('--report-only', action='store_true', help='rebuild REPORT.md for the latest snapshot')
    a = ap.parse_args()
    if a.report_only:
        snaps = sorted(p for p in SNAP.glob('*') if (p / 'topics.json').exists())
        rep = report(snaps[-1], snaps[-2] if len(snaps) > 1 else None, a.me)
        (snaps[-1] / 'REPORT.md').write_text(rep)
        print(rep)
        return
    prevs = sorted(p for p in SNAP.glob('*') if (p / 'topics.json').exists())
    cur = SNAP / time.strftime('%Y-%m-%dT%H%M', time.gmtime())
    cur.mkdir(parents=True, exist_ok=True)
    fetch_leaderboard(cur)
    (cur / 'kernels.json').write_text(json.dumps(fetch_kernels(), indent=1))
    (cur / 'datasets.json').write_text(json.dumps(fetch_datasets(), indent=1))
    (cur / 'topics.json').write_text(json.dumps(fetch_topics(), indent=1))
    rep = report(cur, prevs[-1] if prevs else None, a.me)
    (cur / 'REPORT.md').write_text(rep)
    print(rep)


if __name__ == '__main__':
    main()
