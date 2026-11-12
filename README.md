
# 2026.11.13 IRV_Lab Seminar — 멀티에이전트 개념의 구현과 실험

박천웅 · 발표 제한 20분 + 질의응답.
10.30 발표(AI 에이전트의 개념과 구현 조건)에 이어, 수업 팀 프로젝트로 만든 멀티에이전트 추리 게임
(기차 안의 살인 사건, 에이전트 12명 + GM)을 통해 교재 I(Wooldridge, *An Introduction to MultiAgent Systems*)과
교재 II(Albada, *Building Applications with AI Agents*)의 개념을 어디까지 구현했는지, 왜 그렇게 구현했는지,
실험이 무엇을 보여 줬는지를 공유합니다. 청중은 두 교재와 수업을 접하지 않았다고 가정합니다.

주제: 에이전트가 의도대로 움직이지 않는 이유를 찾아 고치는 과정이자, 협력과 경쟁의 사회 실험.

## 발표 구성

- 본편 **26장**, 부록 **5장**, 전체 **31장**. 본편 계획 **19:00** + 전환 여유 **1:00** = 제한 **20:00**.
  실제 발화 시간은 아직 리허설로 측정하지 않았습니다 (대본 약 4,300자, 초당 5.1자 기준 약 14분).
- 1–2장 (00:00–00:35): 표지, 목차.
- 3–4장 (00:35–02:10): 지난 발표 요약, 두 교재가 보는 멀티에이전트.
- 5–7장 (02:10–04:30): 초기 기획 — 왜 게임인가, 게임 규칙, 구조와 기획 의도(① 학습 ② 인수인계).
- 8–9장 (04:30–06:00): 최초 실험 — 기획 의도와 구현 사이의 간극, 목표를 학습으로 단일화.
- 10–18장 (06:00–13:10): 요소별 개선(무엇을, 왜, 어떻게) — 시간과 판, 정보와 상호작용, 역할 분리, 기억과 학습,
  판단의 주인, 모델 선정, 관계와 성격, 점수와 자율성. 요소마다 시작 시점이 달라 출발점과 도입 날짜를 함께 표기합니다.
- 19–24장 (13:10–17:35): 현재 실험(gpt-6.1-terra, 16판) — 경쟁, 협력, 학습, 성격, 인수인계.
- 25–26장 (17:35–19:00): 교재 개념의 구현 정도, 정리.
- 부록 27–31장: 판별 결과, 최종 누적 순위, 실험 연표와 모델, 해석의 한계, 출처.

## 파일

| 파일 | 용도 |
|---|---|
| [index.html](index.html) | 1280×720 HTML 발표 화면, 발표자 노트, 20분 타이머 |
| [presentation_script.md](presentation_script.md) | 장별 발표 대본과 시간표 |
| [SOURCES.md](SOURCES.md) | 교재 위치, 실험 기록, 수치의 조건과 한계 |
| [validation.json](validation.json) | 헤드리스 Edge로 확인한 레이아웃·상호작용 결과 |
| `assets/` | 슬라이드 목록(`slide_manifest.json`) |
| `.work/` | 분석(`analyze.py`)·덱 빌드(`build_deck.py`, 본문 `content_main.py`)·검증(`validate_deck.py`) 스크립트, 스크린숏 |

## 실행

`index.html`을 Edge 또는 Chrome에서 엽니다. 다른 컴퓨터로 옮길 때는 폴더 전체를 복사합니다.
글꼴은 CDN에서 불러오므로 인터넷 연결이 없으면 대체 글꼴로 표시됩니다.

- 좌우 화살표, PageUp/PageDown: 이동. `Home`: 첫 장. `End`: 마지막 장.
- `M`: 슬라이드 목록과 번호 이동. `N`: 현재 장의 발표자 노트. `F`: 전체 화면.
- `T` 또는 하단 **시작**: 타이머 시작·일시정지. 하단 되돌림 버튼: 초기화.
- 본편 마지막 장 뒤에는 다음 버튼으로 부록에 들어가지 않습니다. 부록은 목록에서 선택합니다.

## 다시 만들기

실험 기록(`F:\multi_agent_AI_Game\unified-packages-v9\runs\`)이 있는 컴퓨터에서 실행합니다.

```powershell
$env:PYTHONUTF8 = "1"
python -B .work\analyze.py        # 실험 기록 → .work\results.json, type_report.txt, v9_check.txt
python -B .work\build_deck.py     # → index.html, presentation_script.md, assets\slide_manifest.json
python -B .work\validate_deck.py  # → validation.json, .work\screenshots\
```
