# Q-Net 001~018 사용자 답안 결선 저장 — 테스트 결과

- 작업 브랜치: `feature/qnet-all-wiring-capture`
- 기준 커밋: `628b92c38fee5a9787159c7996aef8ccae6dbfbc`
- 개발 식별자: `0.14.0-dev12` (제품 표시 버전 `0.13.0` 유지)
- 테스트 데이터: `D:\project\elec\qnet-18` 아래 분리 디렉터리

## 구현 결과

- 001~018 공개 보드/외부 단자에서 사용자 결선을 작성하고 문제·사용자·작업공간별로 저장한다.
- debounce 자동저장, 저장 상태, 마지막 저장 시각, 직렬 저장 큐를 제공한다.
- 명시적 스냅샷, 스냅샷 복제, 안전 JSON export/import를 제공한다.
- 미완성·오결선은 저장하며 공개 단자 기준 구조 경고만 표시한다.
- 008·010·018의 기존 무채점 엔진만 유지하고 나머지는 검증 대기로 표시한다.
- SQLite schema 12는 기존 테이블을 삭제하지 않는 추가형 마이그레이션이다.

## 최종 실행 결과

| 명령 | 결과 |
| --- | --- |
| `scripts/test_all.ps1` | PASS |
| `.venv\Scripts\python.exe -m pytest backend\tests desktop\tests -q` | 263 passed, 0 failed, 1 deprecation warning |
| `.venv\Scripts\python.exe scripts\validate_problems.py` | 23 loaded, 0 errors, 19 intended draft warnings; Q-Net 18/18 |
| `npm test -- --run` | 7 files, 72 passed, 0 failed |
| `npm run typecheck` | PASS |
| `npm run build` | PASS, 64 modules |

## 001~018 검증표

API 매개변수 테스트는 각 문제마다 실제 board 조회, capability 확인, 빈 미완성 draft 저장을 수행했다. UI 공통 기능은 Q001/Q010 브라우저 표본과 프런트 테스트로 확인했다.

| 문제 | 화면/보드 | 결선 저장·복원 | 격리 | 동작 상태 | 결과 |
| --- | --- | --- | --- | --- | --- |
| 001 | PASS | PASS | PASS | 검증 대기 | PASS |
| 002 | PASS | PASS | PASS | 검증 대기 | PASS |
| 003 | PASS | PASS | PASS | 검증 대기 | PASS |
| 004 | PASS | PASS | PASS | 검증 대기 | PASS |
| 005 | PASS | PASS | PASS | 검증 대기 | PASS |
| 006 | PASS | PASS | PASS | 검증 대기 | PASS |
| 007 | PASS | PASS | PASS | 검증 대기 | PASS |
| 008 | PASS | PASS | PASS | 기존 엔진 진입 PASS | PASS |
| 009 | PASS | PASS | PASS | 검증 대기 | PASS |
| 010 | PASS | PASS | PASS | 기존 엔진 진입 PASS | PASS |
| 011 | PASS | PASS | PASS | 검증 대기 | PASS |
| 012 | PASS | PASS | PASS | 검증 대기 | PASS |
| 013 | PASS | PASS | PASS | 검증 대기 | PASS |
| 014 | PASS | PASS | PASS | 검증 대기 | PASS |
| 015 | PASS | PASS | PASS | 검증 대기 | PASS |
| 016 | PASS | PASS | PASS | 검증 대기 | PASS |
| 017 | PASS | PASS | PASS | 검증 대기 | PASS |
| 018 | PASS | PASS | PASS | 기존 엔진 진입 PASS | PASS |

## 2026-08-29 제어함 배치 회귀 수정

- 원인: Q-Net 010을 제외한 보드가 `layout_mode`를 생략하여 서버의 `auto_rows` 정렬이 PDF 좌표를 변경했다.
- 수정: Q-Net 001~018 전부 `fixed`로 통일하여 `board.json`의 PDF 근거 좌표를 그대로 제공한다.
- 회귀 테스트: 18개 원본 좌표와 `/board` API 좌표의 일치 여부를 문제별로 검사한다.
- 관련 테스트: 42 passed. 전체 테스트: Python 263 passed, 프런트 72 passed, 문제 23개/오류 0, Vite 64 modules.
- 브라우저 표본: Q001·Q002·Q013에서 상·하단 기구 분리와 순서를 확인했으며 전체 보드 라벨 겹침은 0건이다.

## 2026-08-29 1회로 2단자 FUSE 제거

- 카탈로그에서 `fuse_single_pole_training` 모델과 자유회로 신규 생성 항목을 제거했다.
- FUSE가 있는 Q-Net 보드와 데모 보드는 모두 한 몸체의 F-1·F-2·F-3·F-4 구성으로 통일했다. Q002는 원래 FUSE가 없는 보드다.
- 런타임의 구형 `fuse` 형식은 4단자 모델로 해석하며, 저장된 편집 가능 자유회로는 인스턴스 ID와 기존 결선을 유지한 채 4단자 모델로 자동 저장 변환한다.
- 전체 테스트: Python 282 passed, 문제 23 loaded/0 errors/19 draft warnings, 프런트 72 passed, TypeScript·Vite 운영 빌드 64 modules.
- 브라우저: Q013에서 F-1·F-2·F-3·F-4 단자만 확인했고, 자유회로 빈보드 팔레트에서 `2회로 4단자 FUSE` 1개와 `2단자 FUSE` 0개를 확인했다.

## 2026-08-29 JSON 내보내기 수정

- 원인: pywebview/WebView2의 `ALLOW_DOWNLOADS` 기본값이 꺼져 있어 데스크톱 앱이 attachment 저장창을 취소했다.
- 수정: 데스크톱 시작 시 다운로드를 허용하고, 최신 결선을 먼저 저장한 뒤 숨김 링크를 DOM에 연결해 다운로드한다. 객체 URL은 클릭 직후가 아닌 지연 해제한다.
- 파일명에서 Windows 금지 문자를 치환하고 `내보내는 중`, 성공, 실패 안내를 표시한다.
- 회귀 테스트: WebView 다운로드 설정 1개와 프런트 JSON 다운로드 상호작용 테스트를 추가했다.
- 전체 테스트: Python 283 passed, 문제 23 loaded/0 errors/19 draft warnings, 프런트 73 passed, TypeScript·Vite 운영 빌드 64 modules.

## 2026-08-29 작업공간 도구줄 표시 수정

- 원인: 일반 결선 화면의 2행 Grid를 사용자 답안 화면의 4개 영역에도 적용하여, 작업공간 도구줄이 DOM에는 존재하지만 화면에서 잘렸다.
- 수정: 사용자 답안 화면에 안내·작업공간 도구·결선 제목·결선판의 4개 명시적 Grid 행을 적용했다.
- 실제 데스크톱 1440×900에서 작업공간, 버전 2개, `JSON 내보내기`, `JSON 가져오기`, 저장 상태와 기존 88개 결선을 동시에 확인했다.
- 전체 테스트: Python 283 passed, 문제 23 loaded/0 errors/19 draft warnings, 프런트 73 passed, TypeScript·Vite 운영 빌드 64 modules.

## 구조 검사 및 저장

| 항목 | 결과 |
| --- | --- |
| 정상·빈·미완성 저장 | PASS |
| 문제 밖/존재하지 않는 단자 | 저장 PASS, 경고 PASS |
| 자기 연결·완전 중복 | 저장 PASS, 경고 PASS |
| 단자 수용량 초과 | 저장 PASS, 경고 PASS |
| 명확한 전원·FUSE 안전 이상 | 저장 PASS, blocking/warning PASS |
| 경고의 정답 데이터 비사용 | PASS |

## 작업공간·스냅샷·JSON

- 문제·작업공간·사용자별 격리: PASS.
- 신규 DB, 반복 초기화, 기존 practice draft 보존: PASS.
- 스냅샷 생성·목록·원본 보존·새 작업공간 복제: PASS.
- export 허용 필드 10개만 노출, Content-Disposition 제공: PASS.
- import schema/문제/버전/500선/1MB 제한 및 새 ID 생성: PASS.
- export/import round-trip과 원본 작업공간 불변: PASS.

## 회귀 및 비노출

- Q008·010·018 practice session 및 공개 요구 동작 회귀: PASS.
- 4단자 FUSE와 자유회로 테스트: 전체 suite에서 PASS.
- 사용자별 SQLite, Windows 연결 종료: PASS.
- 일반 API/export에 `expected_nets`, `allowed_alternatives`, 비공개 operation test 또는 감사 후보 미노출: PASS.
- `frontend/dist`는 `frontend/src` 수정 후 Vite build로 생성했다.

## 미해결사항

- 001~007·009·011~017의 전기·기구 동작 엔진은 근거가 없으므로 이번 작업에서 구현하지 않았다.
- 19개 문제 경고는 기존 Q-Net draft/unverified 상태에 따른 의도된 경고다.
- Starlette/httpx deprecation warning 1건은 기존 의존성 경고이며 테스트 실패가 아니다.
- 실제 브라우저의 저장 API 강제 실패 재현은 수행하지 않았고, 실패 상태·편집 유지·직렬 재시도 로직은 프런트 코드와 테스트 경로로 확인했다.
