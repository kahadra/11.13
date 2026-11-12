"""Numbers for the 2026-11-13 seminar deck, recomputed from the run records.

    PYTHONUTF8=1 python -B analyze.py          # writes results.json (+ tool reports) next to this file

Sources (read-only):
- current experiment  F:/multi_agent_AI_Game/unified-packages-v9/runs/v9-main2-30c-lean (gpt-6.1-terra via Codex CLI, lean, 30 cycles)
- earlier v9 run      .../runs/v9-main-30c (same model, old environment: shared-benefit scoring, no talk rooms)
- v8 campaign         cached rows in 공유자료_멀티에이전트/data/v8.json (gpt-6-luna via Codex CLI)
- experiment-30       numbers from unified-packages-v9/docs/작업_변천사.md §2 (team member's first run)
Tool reports (type_report.py, v9_check.py) are saved as text for the personality / learning slides.
"""
import collections
import json
import sqlite3
import statistics as st
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJ = Path('F:/multi_agent_AI_Game')
V9 = PROJ / 'unified-packages-v9'
CUR = V9 / 'runs' / 'v9-main2-30c-lean'
OLD = V9 / 'runs' / 'v9-main-30c'
V8_CACHE = PROJ / '공유자료_멀티에이전트' / 'data' / 'v8.json'


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def completed(camp):
    """Completed attempts, one per seed (an aborted attempt is rolled back and rerun)."""
    by_seed = {}
    for a in load(camp / 'batch.json')['attempts']:
        if a['status'] == 'completed':
            by_seed[a['seed']] = a
    return [by_seed[s] for s in sorted(by_seed)]


def calls(gdir):
    path = gdir / 'codex-calls.jsonl'
    if not path.exists():
        return
    for line in open(path, encoding='utf-8'):
        try:
            x = json.loads(line)
            u, r = json.loads(x['user']), json.loads(x['response'])
        except Exception:
            continue
        if isinstance(u, dict) and isinstance(r, dict):
            yield x, u, r


def game_rows(camp, deadline=30):
    db = sqlite3.connect(f'file:{camp / "pool.sqlite3"}?mode=ro', uri=True)
    rows = []
    for idx, a in enumerate(completed(camp), 1):
        s = load(a['summary_file'])
        gdir = Path(a['full_record_file']).parent
        g = json.loads(db.execute('select state from games where id=?', (a['game_id'],)).fetchone()[0])
        trades = list(g['trades'].values())
        settled = [t for t in trades if t['status'] == 'settled']
        deceptions = sum(1 for t in settled for v in (t.get('fulfilled') or {}).values() if v is False)
        acc = []
        stall_retry = stand_in = 0
        inter = inter_ins = 0
        for x, u, r in calls(gdir):
            if x.get('gm_remedy') == 'retry':
                stall_retry += 1
            if u.get('phase') == 'interaction':
                inter += 1
                inter_ins += bool((u.get('experience') or {}).get('insights'))
            if u.get('phase') == 'deduction' and (r.get('decision') == 'accuse' or (r.get('action') or {}).get('type') == 'accuse'):
                acc.append(u.get('cycle'))
        fb = g.get('final_feedback') or {}
        combos = [v['final_combinations'] for v in fb.values() if isinstance(v.get('final_combinations'), int)]
        share = g.get('sharing') or {}
        given = sum(v.get('total', 0) for v in share.values())
        budget = sum(v.get('budget', 0) for v in share.values())
        talk = collections.Counter()
        for line in open(gdir / 'detail.jsonl', encoding='utf-8'):
            e = json.loads(line)
            if e.get('event') in ('talk_said', 'talk_intent', 'talk_failed'):
                talk[e['event']] += 1
        rows.append({
            'game': idx, 'seed': a['seed'], 'cycles': s['cycles'], 'minutes': round(s['elapsed_seconds'] / 60),
            'resolution': s['resolution'], 'winners': len(s.get('winners') or []), 'deaths': len(s.get('deaths') or []),
            'accusations': len(acc), 'acc_last_cycle': sum(c == deadline for c in acc), 'acc_cycles': acc,
            'trades_proposed': len(trades), 'settled': len(settled), 'refused': sum(t['status'] == 'refused' for t in trades),
            'deceptions': deceptions, 'shared_points': given, 'share_budget': budget,
            'share_recipients': sum(len(v.get('shares') or []) for v in share.values()),
            'combos_median': st.median(combos) if combos else None, 'combos_min': min(combos) if combos else None,
            'model_calls': s.get('model_calls'), 'model_fallbacks': s.get('model_fallbacks'),
            'player_fallbacks': s.get('player_fallbacks') if isinstance(s.get('player_fallbacks'), int) else None,
            'outages': (s.get('model_outages') or {}).get('outages', 0),
            'outage_paused_s': (s.get('model_outages') or {}).get('paused_seconds', 0),
            'gm_retries': stall_retry, 'interaction_prompts': inter, 'interaction_with_insights': inter_ins, 'talk_lines': talk['talk_said'], 'talk_intents': talk['talk_intent'],
        })
    return rows


def affinity(camp):
    """Reaction deltas from the agents' journals and the stored affinity scores in their memory files."""
    up = down = zero = 0
    for a in completed(camp):
        gdir = Path(a['full_record_file']).parent
        for line in open(gdir / 'detail.jsonl', encoding='utf-8'):
            e = json.loads(line)
            r = e.get('record') or {}
            if e.get('event') == 'agent_journal' and r.get('event') == 'reaction':
                d = (r.get('after') or 0) - (r.get('before') or 0)
                up += d > 0; down += d < 0; zero += d == 0
    scores = [v['affinity'] for p in (camp / 'agent-memory').glob('society_*.json')
              for v in (load(p).get('peers') or {}).values() if 'affinity' in v]
    return {'up': up, 'down': down, 'zero': zero, 'stored_n': len(scores),
            'stored_mean': round(st.mean(scores), 1) if scores else None,
            'stored_at_100': sum(s >= 100 for s in scores)}


def learning(camp):
    """Reflections, plan checks and insight lists in the agents' memory files (ExpeL), plus overlap between agents."""
    ins = {}
    for p in (camp / 'agent-memory').glob('society_*.json'):
        d = load(p)
        ins[d['agent_id']] = [i.get('text', '') for i in d.get('insights') or []]
    texts = collections.Counter(t for v in ins.values() for t in set(v))
    return {'agents': len(ins), 'insights_per_agent': sorted(len(v) for v in ins.values()),
            'shared_texts': sum(1 for t, n in texts.items() if n > 1)}


def learning_trend(camp):
    """Where learning shows: per game, refused trade requests sent again to the same partner later in the game
    (behaviour), and how often the agents' own insights / reflections name that very mistake (words)."""
    db = sqlite3.connect(f'file:{camp / "pool.sqlite3"}?mode=ro', uri=True)
    per_game = []
    for idx, a in enumerate(completed(camp), 1):
        g = json.loads(db.execute('select state from games where id=?', (a['game_id'],)).fetchone()[0])
        tr = list(g['trades'].values())
        refused = [t for t in tr if t['status'] == 'refused']
        key = lambda t: json.dumps(t.get('requested'), sort_keys=True)
        repeat = sum(any(u['proposer'] == t['proposer'] and u['recipient'] == t['recipient'] and key(u) == key(t)
                         and u.get('cycle', 0) > t.get('cycle', 0) for u in tr) for t in refused)
        per_game.append({'game': idx, 'refused': len(refused), 'repeated': repeat})
    rule_agents, admitted, checks, quote = 0, 0, 0, None
    for p in sorted((camp / 'agent-memory').glob('society_*.json')):
        d = load(p)
        rule_agents += any('거절' in (i.get('text') or '') for i in d.get('insights') or [])
        games = d.get('games') or []
        for k, gm in enumerate(games):
            pc = gm.get('plan_check') or ''   # checks the plan written at the end of the previous game
            if pc:
                checks += 1
                if '거절' in pc and ('반복' in pc or '되풀이' in pc):
                    admitted += 1
                    prev = (games[k - 1].get('plan') or '') if k else ''
                    if not quote and '거절' in prev:
                        quote = {'plan': prev[:160], 'check': pc[:170]}
    return {'per_game': per_game, 'agents_with_refusal_rule': rule_agents, 'plan_checks': checks,
            'checks_admitting_repeat': admitted, 'quote': quote}


def refusal_causes(camp):
    """Why the 'repeat after refusal' did not fall: split refusals into the agent's own refusal (it answered, usually
    with words) and the mechanical one (the recipient had already spent its phase action, so the adapter refused for it
    without asking the model; the proposer sees a refusal with no reason). Identical repeat = same partner, same
    requested and same declared types later in the game."""
    act = collections.Counter()
    for a in completed(camp):
        act.update(load(a['summary_file']).get('trade_activity') or {})
    db = sqlite3.connect(f'file:{camp / "pool.sqlite3"}?mode=ro', uri=True)
    rep = collections.Counter()
    visible = hidden = 0
    for a in completed(camp):
        g = json.loads(db.execute('select state from games where id=?', (a['game_id'],)).fetchone()[0])
        tr = sorted(g['trades'].values(), key=lambda t: t.get('cycle', 0))
        req = lambda t: json.dumps(t.get('requested'), sort_keys=True)
        off = lambda t: json.dumps(t.get('declared'), sort_keys=True)
        for t in tr:
            if t['status'] != 'refused':
                continue
            worded = (t.get('messages') or [{}])[-1].get('stage') == 'refuse'
            rep['refused_worded' if worded else 'refused_silent'] += 1
            if not worded:   # why the recipient could not take it: its phase action already went to a trade
                same = [u for u in tr if u is not t and u.get('cycle') == t.get('cycle') and u.get('epoch') == t.get('epoch')]
                own = any(u['proposer'] == t['recipient'] for u in same)
                rep['silent_recipient_proposed'] += own
                rep['silent_crossed'] += any(u['proposer'] == t['recipient'] and u['recipient'] == t['proposer'] for u in same)
                rep['silent_recipient_accepted_other'] += (not own) and any(
                    u['recipient'] == t['recipient'] and (u['accepted'] or u['status'] == 'settled') for u in same)
            u = next((u for u in tr if u['proposer'] == t['proposer'] and u['recipient'] == t['recipient']
                      and u.get('cycle', 0) > t.get('cycle', 0) and req(u) == req(t) and off(u) == off(t)), None)
            if u:
                rep['repeat_after_worded' if worded else 'repeat_after_silent'] += 1
                between = any(v['status'] == 'refused' and v['proposer'] == t['proposer'] and v['recipient'] == t['recipient']
                              and t.get('cycle', 0) < v.get('cycle', 0) < u.get('cycle', 0) and req(v) != req(t) for v in tr)
                hidden += between; visible += not between
    return {'refuse_total': act.get('refuse', 0), 'refuse_no_action_left': act.get('refuse_no_action_left', 0),
            **rep, 'identical_repeats': rep['repeat_after_worded'] + rep['repeat_after_silent'],
            'repeat_prior_refusal_visible': visible, 'repeat_prior_refusal_hidden': hidden}


def talk_effect(camp):
    """Did talking lead to dealing? Pairs of players in the same room in a cycle, split by whether one heard the other
    in that cycle's talk room; outcome = a trade proposed / settled between them in that cycle. Selection caveat: agents
    choose whom to talk to, so this is association, not effect."""
    import itertools
    db = sqlite3.connect(f'file:{camp / "pool.sqlite3"}?mode=ro', uri=True)
    C = collections.Counter()
    for a in completed(camp):
        g = json.loads(db.execute('select state from games where id=?', (a['game_id'],)).fetchone()[0])
        cid = {aid: p['character_id'] for aid, p in g['players'].items()}
        talked = set()
        for line in open(Path(a['full_record_file']).parent / 'detail.jsonl', encoding='utf-8'):
            e = json.loads(line)
            r = e.get('record') or {}
            if e.get('event') == 'agent_journal' and r.get('event') == 'claim_heard' and r.get('context') == '담화방':
                me = cid.get(e.get('agent_id'))
                if me is not None:
                    talked.add((r.get('cycle'), frozenset((me, r.get('from_character')))))
        deals = collections.defaultdict(lambda: [0, 0])
        for t in g['trades'].values():
            k = (t.get('cycle'), frozenset((cid[t['proposer']], cid[t['recipient']])))
            deals[k][0] += 1
            deals[k][1] += t['status'] == 'settled'
        players = set(cid.values())
        for p in g.get('placements') or []:
            rooms = collections.defaultdict(list)
            for ch, room in p['rooms'].items():
                if int(ch) in players:
                    rooms[room].append(int(ch))
            for chs in rooms.values():
                for x, y in itertools.combinations(chs, 2):
                    k = (p['cycle'], frozenset((x, y)))
                    grp = 'talk' if k in talked else 'no_talk'
                    C[grp] += 1
                    C[grp + '_proposed'] += deals[k][0] > 0
                    C[grp + '_settled'] += deals[k][1] > 0
    return dict(C)


def accusation_incentive(camp):
    """Why accusations moved earlier under winner-take-all (A39): at each deduction decision, compare the score of a wrong
    accusation (mission points kept, -20) with what surviving gives (0 if someone else wins, -10 if unsolved). 'free' =
    a wrong accusation is no worse than surviving. Outcome: an accuser who is in the winners list was right."""
    import re
    db = sqlite3.connect(f'file:{camp / "pool.sqlite3"}?mode=ro', uri=True)
    C = collections.Counter()
    for a in completed(camp):
        s = load(a['summary_file'])
        wins = {w['character_id'] if isinstance(w, dict) else None for w in s.get('winners') or []}
        for x, u, r in calls(Path(a['full_record_file']).parent):
            if u.get('phase') != 'deduction':
                continue
            am = u.get('accuse_math') or {}
            sw, so, su = am.get('score_if_wrong'), am.get('score_if_someone_else_wins'), am.get('score_if_unsolved_and_alive')
            if sw is None or so is None:
                continue
            free = sw >= max(so, su if su is not None else -999)
            acc = r.get('decision') == 'accuse' or (r.get('action') or {}).get('type') == 'accuse'
            early = u.get('cycle') != 30
            tag = 'free' if free else 'not_free'
            C[f'{tag}_decisions'] += 1
            if early:
                C[f'{tag}_early_decisions'] += 1
            if acc:
                C[f'{tag}_acc'] += 1
                C[f'{tag}_acc_early'] += early
                C[f'{tag}_correct'] += ((u.get('me') or {}).get('character_id') in wins)
                text = (r.get('consideration') or '') + json.dumps(r.get('deduction_math') or {}, ensure_ascii=False)
                C[f'{tag}_mentions_mission'] += bool(re.search(r'미션|임무', text))
    # final standings: best rank reached by an agent who never won, and its wrong-death points
    rows = []
    for r in db.execute('select * from agents'):
        d = json.loads(r[1])
        if d.get('pool_role') != 'player':
            continue
        H = [h for h in d['history'] if h.get('resolution') != 'operator_stopped']
        rows.append({'mbti': d.get('fixed_mbti'), 'cum': d.get('cumulative_score'), 'wins': sum(h['outcome'] == 'win' for h in H),
                     'wrong_deaths': sum(not h['survived'] for h in H),
                     'death_points': sum(h['final_score'] for h in H if not h['survived']),
                     'win_points': sum(h['final_score'] for h in H if h['outcome'] == 'win'),
                     'alive_points': sum(h['final_score'] for h in H if h['survived'] and h['outcome'] != 'win'),
                     'games': len(H), 'gifts_in': sum(x['points'] for x in d.get('shares_received') or []),
                     'gifts_out': sum(x['points'] for x in d.get('shares_given') or [])})
    rows = [x for x in rows if x['cum'] is not None]  # cumulative score exists from A40 on
    rows.sort(key=lambda x: -x['cum'])
    for i, x in enumerate(rows, 1):
        x['rank'] = i
    nowin = [x for x in rows if x['wins'] == 0]
    out = dict(C)
    out['standings'] = rows
    out['best_no_win'] = nowin[0] if nowin else None
    out['death_points_total'] = sum(x['death_points'] for x in rows)
    out['win_points_total'] = sum(x['win_points'] for x in rows)
    return out


def gm_memory(camp):
    d = load(camp / 'agent-memory' / 'gm_society_gm.json')
    recent = sorted((d.get('model_calls') or [])[-300:])
    p90 = recent[int(0.9 * (len(recent) - 1))] if recent else None
    deadline = None if len(recent) < 20 else max(60, min(300, 4 * p90))
    return {'playbook': d.get('playbook'), 'model_calls_seen': len(d.get('model_calls') or []),
            'p90_seconds': p90, 'learned_deadline_s': deadline, 'escalations': len(d.get('escalations') or [])}


def tool_report(script, out_name):
    res = subprocess.run([sys.executable, '-B', str(V9 / 'tools' / script), str(V9), CUR.name],
                         cwd=V9, capture_output=True, text=True, encoding='utf-8', env={'PYTHONUTF8': '1', **__import__('os').environ})
    (HERE / out_name).write_text(res.stdout + res.stderr, encoding='utf-8')
    return res.returncode


def summarize(rows):
    n = len(rows)
    acc = sum(r['accusations'] for r in rows)
    wins = sum(r['winners'] for r in rows)
    return {
        'games': n, 'games_solved': sum(r['winners'] > 0 for r in rows), 'winners': wins,
        'accusations': acc, 'correct': wins, 'acc_last_cycle': sum(r['acc_last_cycle'] for r in rows),
        'settled': sum(r['settled'] for r in rows), 'refused': sum(r['refused'] for r in rows),
        'deceptions': sum(r['deceptions'] for r in rows),
        'shared_points': sum(r['shared_points'] for r in rows), 'share_budget': sum(r['share_budget'] for r in rows),
        'minutes_median': st.median(r['minutes'] for r in rows) if rows else None,
        'solve_cycles': [r['cycles'] for r in rows if r['winners']],
        'model_fallbacks': sum(r['model_fallbacks'] or 0 for r in rows),
        'model_calls': sum(r['model_calls'] or 0 for r in rows),
        'outages': sum(r['outages'] for r in rows), 'talk_lines': sum(r['talk_lines'] for r in rows),
    }


def main():
    cur = game_rows(CUR)
    old = game_rows(OLD)
    out = {
        'experiment30': {'games': 30, 'agents_per_game': 12, 'decisions': 14347, 'accusations': 0, 'winners': 0,
                         'end_cycles': '12–15', 'deadline_cycles': 120, 'time_limit_s': 3600,
                         'combos_agent_mean': 536, 'combos_pooled': 94, 'source': '작업_변천사.md §2'},
        'v8': {'rows': load(V8_CACHE)} if V8_CACHE.exists() else {},
        'v9_old': {'rows': old, 'summary': summarize(old), 'affinity': affinity(OLD), 'incentive': accusation_incentive(OLD)},
        'current': {'rows': cur, 'summary': summarize(cur), 'affinity': affinity(CUR), 'learning': learning(CUR),
                    'trend': learning_trend(CUR), 'refusals': refusal_causes(CUR), 'talk_effect': talk_effect(CUR), 'incentive': accusation_incentive(CUR),
                    'gm': gm_memory(CUR)},
    }
    v8 = out['v8'].get('rows') or []
    out['v8']['summary'] = {'games': len(v8), 'games_solved': sum(r['winners'] > 0 for r in v8),
                            'accusations': sum(len(r['accusations']) for r in v8),
                            'settled': sum(r['settled'] for r in v8), 'refused': sum(r['refused'] for r in v8)}
    out['tool_returncodes'] = {'type_report': tool_report('type_report.py', 'type_report.txt'),
                               'v9_check': tool_report('v9_check.py', 'v9_check.txt')}
    (HERE / 'results.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({k: out[k].get('summary') for k in ('v8', 'v9_old', 'current')}, ensure_ascii=False, indent=1))
    print('affinity', out['current']['affinity'], 'learning', out['current']['learning'], 'gm', {k: v for k, v in out['current']['gm'].items() if k != 'playbook'})


if __name__ == '__main__':
    main()
