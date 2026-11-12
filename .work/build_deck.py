"""Build the 2026-11-13 IRV_Lab seminar deck: implementing multi-agent concepts in a competitive deduction game.

Flow (user's decision 2026-11-12): recap of 10.30 -> initial plan -> first experiment (gap between the plan's intent and
its implementation) -> what was improved, why and how, organised by ELEMENT (versions only briefly) -> current experiment
-> overall implications (how far the two textbooks' concepts were implemented).

Reuses the 10.30 deck's CSS, navigation, notes and timer. Every number on a slide comes from results.json
(analyze.py, recomputed from the run records) or from the tool reports saved next to it.
Outputs: ../index.html, ../presentation_script.md, ../assets/slide_manifest.json
"""
import html
import json
import re
import statistics as st
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
root = HERE.parent
old = (root.parent / "10.30/index.html").read_text(encoding="utf8")
DATE, LIMIT = "2026.11.13", 1200
R = json.loads((HERE / "results.json").read_text(encoding="utf8"))
TYPE = (HERE / "type_report.txt").read_text(encoding="utf8")
CHECK = (HERE / "v9_check.txt").read_text(encoding="utf8")
esc = html.escape

# ---------- numbers ------------------------------------------------------------------------------
E30 = R["experiment30"]
V8 = R["v8"]["summary"]
OLD, OLDA = R["v9_old"]["summary"], R["v9_old"]["affinity"]
CUR, CA, CL, GM = R["current"]["summary"], R["current"]["affinity"], R["current"]["learning"], R["current"]["gm"]
ROWS = R["current"]["rows"]
TR = R["current"]["trend"]
TE = R["current"]["talk_effect"]
TARGET_GAMES = 16


def grab(pattern, text, cast=float, group=1):
    m = re.search(pattern, text, re.S)
    if not m:
        raise SystemExit(f"pattern not found: {pattern}")
    return cast(m.group(group))


def axis_block(ax):
    return TYPE.split(f"== {ax}", 1)[1].split("\n==", 1)[0] if f"== {ax}" in TYPE else ""


R1_REFL = grab(r"R1 reflections (\d+)", CHECK, int)
R1_PLAN = grab(r"with plan_check (\d+)", CHECK, int)
U1_FOLLOW = grab(r"decision follows own higher EV (\d+)/(\d+)", CHECK, int)
U1_TOTAL = grab(r"decision follows own higher EV (\d+)/(\d+)", CHECK, int, 2)
U1_UNIFORM = grab(r"own chance x combinations \(1 = uniform\) median ([\d.]+)", CHECK)
X1_REPEAT = grab(r"X1 same request to the same partner after a refusal: (\d+)/(\d+)", CHECK, int)
X1_REFUSALS = grab(r"X1 same request to the same partner after a refusal: (\d+)/(\d+)", CHECK, int, 2)
TF = axis_block("T vs F")
T_PRESS = grab(r"T:.*?interrogate\+threaten \d+/\d+ \((\d+)%\)", TF, int)
F_PRESS = grab(r"F:.*?interrogate\+threaten \d+/\d+ \((\d+)%\)", TF, int)
JP = axis_block("J vs P")
J_COUNTER = grab(r"J:.*?counter \d+/\d+ \((\d+)%\)", JP, int)
P_COUNTER = grab(r"P:.*?counter \d+/\d+ \((\d+)%\)", JP, int)
SNB = axis_block("S vs N")
S_CHANCE = grab(r"S:.*?own chance x combos \(1 = uniform\) mean ([\d.]+)", SNB)
N_CHANCE = grab(r"N:.*?own chance x combos \(1 = uniform\) mean ([\d.]+)", SNB)
J_REF = grab(r"J:.*?delta after a refused trade ([\d.]+)", JP)
P_REF = grab(r"P:.*?delta after a refused trade ([\d.]+)", JP)
TALK = TYPE.split("== talk rooms", 1)[1].split("\n==", 1)[0]
E_LAST = grab(r"E: talk.*?accusations at the last cycle \d+/\d+ \((\d+)%\)", TALK, int)
I_LAST = grab(r"I: talk.*?accusations at the last cycle \d+/\d+ \((\d+)%\)", TALK, int)
E_INTENT = grab(r"E: talk intent \d+/\d+ \((\d+)%\)", TALK, int)
I_INTENT = grab(r"I: talk intent \d+/\d+ \((\d+)%\)", TALK, int)
LEAVES = sum(int(x) for x in re.findall(r"leave (\d+)/\d+ \(", TALK.split("\n  I:")[0])) + \
    sum(int(x) for x in re.findall(r"leave (\d+)/\d+ \(", "\n  I:" + TALK.split("\n  I:")[1].split("\n  S:")[0]))

n_games = CUR["games"]
done = n_games >= TARGET_GAMES
mins = CUR["minutes_median"]
per_cycle = mins / 30
hours_120 = per_cycle * 120 / 60
old_last = OLD["acc_last_cycle"] / OLD["accusations"]
cur_last = CUR["acc_last_cycle"] / CUR["accusations"]
old_acc_rate = OLD["correct"] / OLD["accusations"]
cur_acc_rate = CUR["correct"] / CUR["accusations"]
settled_pg = CUR["settled"] / n_games
old_settled_pg = OLD["settled"] / OLD["games"]
half = n_games // 2
first, second = ROWS[:half], ROWS[half:]


def pct(x): return "–" if x is None else f"{100 * x:.0f}%"


# ---------- HTML helpers -------------------------------------------------------------------------
def box(title, text, color="blue"): return f'<div class="box {color}"><h3>{title}</h3><p>{text}</p></div>'
def lead(s): return f'<p class="lead">{s}</p>'
def note(s): return f'<p class="reading">{s}</p>'
def take(s): return f'<div class="takeaway">{s}</div>'
def grid(*items, cols=2, cls=""): return f'<div class="grid-{cols} {cls}">' + "".join(f'<div class="cell">{x}</div>' for x in items) + "</div>"


def table(headers, rows, cls=""):
    return (f'<table class="data-table {cls}"><thead><tr>' + "".join(f"<th>{h}</th>" for h in headers) + "</tr></thead><tbody>"
            + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows) + "</tbody></table>")


def tiles(items):
    return '<div class="tiles">' + "".join(f'<div class="tile"><b>{v}</b><span>{l}</span></div>' for v, l in items) + "</div>"


def elem(problem, basis, change, check, lesson):
    """One improvement element: problem -> textbook basis -> what changed -> what we saw, then a one-line lesson."""
    cols = [("문제", "p", problem), ("근거", "b", basis), ("바꾼 것", "c", change), ("확인", "k", check)]
    return ('<div class="elem">' + "".join(f'<div class="ecol {k}"><h4>{t}</h4><div>{body}</div></div>' for t, k, body in cols) + "</div>"
            + take(lesson))


def ul(*items): return "<ul class=\"tight\">" + "".join(f"<li>{x}</li>" for x in items) + "</ul>"


def status(kind):
    return {"구현": '<span class="tag ok">구현</span>', "부분": '<span class="tag part">부분</span>',
            "미구현": '<span class="tag bad">미구현</span>'}[kind]


def bars(cats, series, w=560, h=270):
    """Grouped vertical bars, values 0..1. series: [(name, color, [v per cat])]."""
    pad_l, pad_b, pad_t = 44, 46, 26
    plot_w, plot_h = w - pad_l - 10, h - pad_b - pad_t
    gw = plot_w / len(cats)
    bw = min(56, (gw - 30) / len(series))
    out = [f'<svg class="chart" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img">']
    for t in (0, .25, .5, .75, 1):
        y = pad_t + plot_h * (1 - t)
        out.append(f'<line x1="{pad_l}" x2="{w - 10}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/>'
                   f'<text x="{pad_l - 8}" y="{y + 5:.1f}" class="axis" text-anchor="end">{pct(t)}</text>')
    for ci, c in enumerate(cats):
        x0 = pad_l + gw * ci + (gw - bw * len(series) - 3 * (len(series) - 1)) / 2
        for si, (name, color, vals) in enumerate(series):
            v = vals[ci]
            bh = plot_h * v
            x, y = x0 + si * (bw + 3), pad_t + plot_h - bh
            r = min(4, bh / 2)
            out.append(f'<path d="M{x:.1f},{pad_t + plot_h} V{y + r:.1f} Q{x:.1f},{y:.1f} {x + r:.1f},{y:.1f} H{x + bw - r:.1f} '
                       f'Q{x + bw:.1f},{y:.1f} {x + bw:.1f},{y + r:.1f} V{pad_t + plot_h}Z" fill="{color}"><title>{esc(name)} · {esc(c)}: {pct(v)}</title></path>'
                       f'<text x="{x + bw / 2:.1f}" y="{y - 7:.1f}" class="val" text-anchor="middle">{pct(v)}</text>')
        out.append(f'<text x="{pad_l + gw * ci + gw / 2:.1f}" y="{h - 18}" class="axis cat" text-anchor="middle">{esc(c)}</text>')
    out.append(f'<line x1="{pad_l}" x2="{w - 10}" y1="{pad_t + plot_h}" y2="{pad_t + plot_h}" class="base"/></svg>')
    legend = "".join(f'<span><i style="background:{c}"></i>{esc(n)}</span>' for n, c, _ in series)
    return f'<figure class="chart-fig">{"".join(out)}<figcaption class="legend">{legend}</figcaption></figure>'


BLUE, AMBER = "#2867d8", "#b7791f"
slides = []


def add(title, section, seconds, body, notes, source, short=""):
    slides.append(dict(title=title, section=section, seconds=seconds, body=body, notes=notes, source=source, short=short, aside=""))


exec((HERE / "content_main.py").read_text(encoding="utf8"))

MAIN = len(slides)
assert sum(s["seconds"] for s in slides) == 1140, sum(s["seconds"] for s in slides)


def app(title, body, notes, source):
    add(title, "Appendix · Q&A", 0, body, notes, source)


app("부록 · 현재 실험 판별 결과",
    table(["판", "결과", "사이클", "정답/탈락", "추리 도전 (마지막 사이클)", "성사/거절 거래", "분배 점수", "판 끝 남은 조합 (중앙값)", "분"],
          [[r["game"], "정답" if r["winners"] else "미해결", r["cycles"], f'{r["winners"]}/{r["deaths"]}', f'{r["accusations"]} ({r["acc_last_cycle"]})',
            f'{r["settled"]}/{r["refused"]}', r["shared_points"], "–" if r["combos_median"] is None else f'{r["combos_median"]:.0f}', r["minutes"]] for r in ROWS],
          "compact-table small-rows center"),
    "현재 실험의 판별 결과입니다. 남은 조합은 엔진이 판 끝에 각자의 단서로 계산한 값이고, 에이전트에게는 보이지 않습니다.",
    "v9-main2-30c-lean · results.json")

app("부록 · 실험 연표와 모델",
    table(["단계", "기간", "모델", "규모", "결과"], [
        ["최초 실험", "11/3–6", "gpt-6-luna", "120사이클(실제 1시간 제한) × 30판", "추리 도전 0"],
        ["수정·점검 캠페인", "11/6–8", "gpt-6-luna via Codex CLI", "20–30사이클 × 1–10판씩", "정답 1판(점검), 나머지 0"],
        ["첫 본 캠페인", "11/8–9", "gpt-6-luna via Codex CLI", f"30사이클 × {V8['games']}판", f"정답 {V8['games_solved']}판, 추리 도전 {V8['accusations']}건"],
        ["개선판 본 실험", "11/9–10", "gpt-6.1-terra via Codex CLI", f"30사이클 × {OLD['games']}판", f"정답자 나온 판 {OLD['games_solved']}, 추리 도전 {OLD['accusations']}회"],
        ["현재 실험", "11/11–12", "gpt-6.1-terra via Codex CLI (경량)", f"30사이클 × {n_games}판", f"정답자 나온 판 {CUR['games_solved']}, 추리 도전 {CUR['accusations']}회"]],
        "compact-table"),
    "실험 연표와 모델입니다. Codex CLI로 돌린 실행은 API 호출이 아니라 로컬 Codex 도구를 거친 결과입니다.",
    "작업 변천사 · 변경 기록 · batch.json")

app("부록 · 해석의 한계",
    grid(box("판 수", "현재 실험은 판 수가 적고, 정답 여부는 운의 영향이 크다", "amber"),
         box("동시에 바뀐 것", "이전 환경과의 차이에는 점수·담화방 변경과 경량 프롬프트가 함께 들어 있다", "amber"),
         box("모델 하나", "각 단계는 한 모델로 돌렸고, 첫 본 캠페인과 개선판은 모델이 다르다", "amber"),
         box("직접 만든 측정", "모델 측정 상황과 성격 예측표는 직접 설계한 것으로, 외부 기준과 비교하지 않았다", "amber"), cols=2),
    "수치를 읽을 때의 한계입니다.",
    "SOURCES.md")

app("부록 · 출처",
    table(["구분", "내용"], [
        ["교재 I", "M. Wooldridge, <i>An Introduction to MultiAgent Systems</i>, 2nd ed. — §2.2, §7.1, §11.1, §11.5, §12.4, Ch.13, §15.4"],
        ["교재 II", "M. Albada, <i>Building Applications with AI Agents</i>, O’Reilly — Ch.5–13"],
        ["팀 문서", "1쪽 제안서(2026.10.05), 게임 기획서 v1.0–v1.3"],
        ["실험 기록", "experiment-30, v8-main-30c, v9-main-30c, v9-main2-30c-lean (batch.json, 판별 요약, 모델 호출 기록, 에이전트 기억 파일)"],
        ["분석", "analyze.py → results.json, type_report.py, v9_check.py"]], "compact-table"),
    "출처입니다.", "SOURCES.md")

# ---------- render (same engine as 10.30) --------------------------------------------------------
css = re.search(r"<style>(.*?)</style>", old, re.S)[1]
css += r"""
.toc-grid.six{grid-template-columns:repeat(3,1fr)}.toc-grid.six .toc-item{min-height:112px;padding:16px 18px}
.tiles{display:grid;grid-auto-flow:column;grid-auto-columns:1fr;gap:14px;margin:4px 0 14px}
.tile{background:white;border:1px solid var(--line);border-radius:12px;padding:14px 16px}.tile b{display:block;font-size:34px;font-weight:800;color:#172840;line-height:1.15}
.tile span{display:block;font-size:14.5px;color:#61708a;margin-top:4px;line-height:1.35}
.wide-left .tiles{grid-auto-flow:row}.wide-left .tile b{font-size:28px}
.cond-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:6px}
.cond{background:white;border:1px solid var(--line);border-top:4px solid var(--teal);border-radius:12px;padding:14px 14px;min-height:150px}
.cond b{display:block;font-size:18px;color:#172840;margin-bottom:8px}.cond p{font-size:15.5px;line-height:1.5;color:#3f4f68}
.arch{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:14px}
.abox{background:white;border:1px solid var(--line);border-left:5px solid #2867d8;border-radius:12px;padding:12px 16px}
.abox h3{font-size:19px;margin-bottom:4px}.abox p{font-size:15px;color:#3f4f68;line-height:1.45}.abox.gm{border-left-color:#b7791f}.abox.pl{border-left-color:#0d6f6a}
.elem{display:grid;grid-template-columns:1fr 1fr 1.15fr .85fr;gap:12px;height:392px}
.ecol{background:white;border:1px solid var(--line);border-radius:12px;padding:12px 14px;min-width:0}
.ecol h4{font-size:15px;font-weight:800;letter-spacing:.5px;margin:0 0 8px;padding:3px 10px;border-radius:6px;display:inline-block;color:white}
.ecol.p h4{background:#a3271b}.ecol.b h4{background:#5b3f94}.ecol.c h4{background:#0d6f6a}.ecol.k h4{background:#2867d8}
.ecol.c{background:#f2faf9;border-color:#bfe3df}
ul.tight{margin:0;padding-left:20px;list-style:disc}ul.tight li{font-size:16.5px;line-height:1.5;color:#22324c;margin-bottom:9px}ul.tight li::marker{color:#9aa6b8}
.emap{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:18px}
.echip{background:white;border:1px solid var(--line);border-radius:12px;padding:12px 14px;display:grid;grid-template-columns:34px 1fr;column-gap:10px;align-items:center}
.echip span{grid-row:span 2;width:34px;height:34px;border-radius:50%;background:#172840;color:white;display:grid;place-items:center;font-weight:800}
.echip b{font-size:18px;color:#172840}.echip small{font-size:13.5px;color:#61708a;line-height:1.35}
.vline{display:grid;grid-template-columns:repeat(4,1fr);gap:0;border-top:3px solid #c9d3e2;padding-top:10px}
.vline div{padding:0 12px 0 0;position:relative}.vline div:before{content:'';position:absolute;top:-17px;left:0;width:11px;height:11px;border-radius:50%;background:#172840}
.vline b{display:block;font-size:14px;color:#0d6f6a}.vline span{font-size:14px;color:#3f4f68;line-height:1.4}
.jflow{display:grid;grid-template-columns:1fr 1fr 1.15fr;gap:22px;margin-bottom:12px}
.jcard{position:relative;background:white;border:1px solid var(--line);border-radius:12px;padding:10px 14px;min-height:150px}
.jcard:not(:last-child):after{content:'→';position:absolute;right:-18px;top:50%;transform:translateY(-50%);color:var(--teal);font-weight:800;font-size:18px}
.jcard.f{background:#f2faf9;border-color:#bfe3df}
.jcard h4,.jbox h4{font-size:14px;font-weight:800;letter-spacing:.4px;margin:0 0 6px;padding:2px 9px;border-radius:6px;display:inline-block;color:white}
.jcard.i h4{background:#61708a}.jcard.s h4{background:#a3271b}.jcard.f h4{background:#0d6f6a}
.jlow{display:grid;grid-template-columns:1fr 1.25fr;gap:14px}
.jbox{background:white;border:1px solid var(--line);border-radius:12px;padding:10px 14px}
.jbox.t h4{background:#5b3f94}.jbox.d h4{background:#b7791f}.jbox.d{background:#fffaf0;border-color:#f0dcb4}
.jflow ul.tight li,.jlow ul.tight li{font-size:14.5px;line-height:1.42;margin-bottom:4px}
.deck .takeaway{margin-top:12px}
.echip.how{grid-column:span 1;display:block;background:#172840}.echip.how b{color:white;font-size:16px;display:block}.echip.how small{color:#cfe0f5}
.grid-2.diag-left{grid-template-columns:380px 1fr}.diag-left .agent-diagram .part{width:150px;height:66px;font-size:17px}.diag-left .agent-diagram .p1,.diag-left .agent-diagram .p3{left:14px}.diag-left .agent-diagram .p2,.diag-left .agent-diagram .p4{right:14px}.diag-left .agent-diagram .core{width:160px;height:90px}
.jwhen{display:block;font-size:12.5px;font-weight:700;color:#61708a;margin:-2px 0 5px}.jcard.f .jwhen{color:#0d6f6a}.when{display:inline-block;font-size:11.5px;font-weight:800;color:white;background:#8a97ab;border-radius:4px;padding:0 6px;margin-right:6px;vertical-align:1px}
.why-list{background:white;border:1px solid var(--line);border-radius:12px;padding:12px 16px}.why-list h3{font-size:17px;margin-bottom:8px}.why-list>div{display:flex;gap:10px;margin-bottom:8px}.why-list b{flex:none}.why-list p{font-size:14.5px;line-height:1.45;color:#22324c}.why-list .hit{background:#fff3dc;border-left:4px solid #d09a34;border-radius:0 8px 8px 0;padding:6px 8px}
.tag.part{background:#fff3d6;color:#7a5200}.tag.part:before{content:'◐ '}
.data-table td small{display:block;font-size:12.5px;color:#61708a;margin-top:2px}
"""


def clock(n): return f"{n // 60:02}:{n % 60:02}"


t = 0
for s in slides:
    s["start"] = clock(t); t += s["seconds"]; s["end"] = clock(t); s["duration"] = clock(s["seconds"])
    s["page"] = 1; s["cue"] = ""


def fill_times(text):
    text = re.sub(r"@@S(\d+)@@", lambda m: slides[int(m.group(1)) - 1]["start"], text)
    return re.sub(r"@@E(\d+)@@", lambda m: slides[int(m.group(1)) - 1]["end"], text)


for s in slides:
    s["body"] = fill_times(s["body"])
parts = []
for i, s in enumerate(slides):
    if i == 0:
        body = ('<div class="title-top"><span class="pill dark">MULTI-AGENT · CONCEPTS TO IMPLEMENTATION</span><span>IRV_LAB SEMINAR · 20 MIN</span></div>'
                '<div class="title-main"><div class="title-rule"></div><h1>멀티에이전트 개념의<br>구현과 실험</h1>'
                '<h2>경쟁 추리 게임 속 LLM 에이전트 12명 — 기획 의도와 구현 사이</h2>'
                '<p class="title-korean">지난 발표(10.30, AI 에이전트의 개념과 구현 조건)에 이어서</p>'
                '<p class="authors">수업 팀 프로젝트 · 교재 I (Wooldridge) · 교재 II (Albada)</p></div>'
                f'<div class="title-meta"><div><small>PRESENTER</small><b>박천웅</b></div><div><small>AFFILIATION</small><b>IRV_Lab</b></div>'
                f'<div><small>DATE</small><b>2026. 11. 13.</b></div><div><small>TIME LIMIT</small><b>20 min</b></div></div>')
    else:
        stamp = f'{s["start"]}–{s["end"]} · {s["duration"]}' if s["seconds"] else "질의응답용 · 본편 시간 미포함"
        body = (f'<header class="slide-header"><div><div class="eyebrow">{s["section"]}</div><h2 class="slide-title">{s["title"]}</h2></div>'
                f'<div class="slide-kicker">Multi-Agent · {DATE}<br>{stamp}</div></header><div class="slide-body">{s["body"]}</div>'
                f'<footer class="slide-footer"><span class="source"><a href="SOURCES.md" target="_blank">{esc(s["source"])}</a></span>'
                f'<span class="slide-no">{i + 1:02} / {len(slides):02} · ' + ("MAIN" if i < MAIN else "APPENDIX") + "</span></footer>")
    parts.append(f'<section class="slide {"title-slide" if i == 0 else ""}" data-title="{esc(s["title"])}" aria-label="{i + 1}. {esc(s["title"])}">{body}</section>')

controls = old[old.index("<nav"):old.index("<script>")]
controls = re.sub(r'max="\d+"', f'max="{len(slides)}"', controls)
controls = re.sub(r"/ \d+</label>", f"/ {len(slides)}</label>", controls)
js = old[old.index("const slides=[...document.querySelectorAll"):old.rindex("</script>")]
js = re.sub(r"const mainCount=\d+", f"const mainCount={MAIN}", js)
js = js.replace("| AI Agents Seminar", "| Multi-Agent Seminar").replace("toolUseTimer", "multiAgentTimer")
assert f"const mainCount={MAIN}" in js and "multiAgentTimer" in js
head = old[:old.index("<style>")]
head = re.sub(r'<meta name="description" content="[^"]*">',
              '<meta name="description" content="멀티에이전트 개념의 구현과 실험 · IRV_Lab 2026.11.13 · 박천웅 · 20분 세미나">', head)
head = re.sub(r"<title>.*?</title>", "<title>Multi-Agent · 2026.11.13 Seminar</title>", head)
data = [{k: v for k, v in s.items() if k != "body"} for s in slides]
result = (head + "<style>" + css + '</style></head><body class="deck"><main class="viewport"><div id="deck">' + "".join(parts)
          + "</div></main>" + controls + "<script>const slideData=" + json.dumps(data, ensure_ascii=False) + ";\n" + js + "</script></body></html>")
(root / "index.html").write_text(result, encoding="utf8")
(root / "assets").mkdir(exist_ok=True)
(root / "assets/slide_manifest.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf8")

chars = sum(len(s["notes"]) for s in slides[:MAIN])
RATE = 5.1   # user's measured speaking rate (chars/s, 2026-11-01 rehearsal)
script = ["# 멀티에이전트 개념의 구현과 실험 — 세미나 발표 대본", "", f"박천웅 · IRV_Lab · {DATE}", "",
          f"본편 **{MAIN}장 · 계획 19:00**, 전환 여유 **1:00**, 발표 제한 **20:00**. 부록 {len(slides) - MAIN}장은 본편에 포함하지 않습니다.",
          f"본편 대본 {chars:,}자 · 발표자 리허설 속도(초당 {RATE}자) 기준 약 {chars / RATE / 60:.1f}분. 실제 시간은 리허설로 확인해야 합니다.",
          "" if done else f"> 실험 진행 중 생성: 현재 실험 {n_games}/{TARGET_GAMES}판 기준 수치입니다.", "",
          "## 시간 운영", "",
          "- 표지에서 `T`를 눌러 20분 타이머를 시작합니다. `T`는 일시정지/재개, `↺`는 초기화입니다.",
          "- 체크포인트: @@E4@@ 지난 발표 요약 종료 / @@E7@@ 초기 기획 종료 / @@E9@@ 최초 실험 종료 / @@E18@@ 개선 요소 종료 / @@E24@@ 현재 실험 종료 / @@E26@@ 정리 종료.",
          "- 1분 이상 늦으면 요소 ③(역할 분리)과 ⑤(판단의 주인)는 ‘바꿔야 했던 이유’ 한 줄만 말하고 넘어갑니다.", "",
          "## 본편 시간표", "", "| 장 | 주제 | 구간 | 배정 |", "|---|---|---|---|"]
for i, s in enumerate(slides[:MAIN]):
    script.append(f'| {i + 1:02} | {s["title"]} | {s["start"]}–{s["end"]} | {s["duration"]} |')
for i, s in enumerate(slides):
    script += ["", f"## Slide {i + 1:02}. {s['title']}", "",
               f"- 시간: {s['start']}–{s['end']} / {s['duration']} · 대본 {len(s['notes'])}자 (약 {len(s['notes']) / RATE:.0f}초)" if s["seconds"] else "- 시간: 질의응답용 · 본편 미포함",
               f"- 근거: {s['source']}", "", s["notes"]]
(root / "presentation_script.md").write_text(fill_times("\n".join(script)) + "\n", encoding="utf8")
print(json.dumps({"slides": len(slides), "main": MAIN, "games": n_games, "script_chars_main": chars,
                  "est_minutes": round(chars / RATE / 60, 1),
                  "over": [(i + 1, s["title"], len(s["notes"]), s["seconds"]) for i, s in enumerate(slides[:MAIN]) if len(s["notes"]) / RATE > s["seconds"] * 1.15]},
                 ensure_ascii=False))
