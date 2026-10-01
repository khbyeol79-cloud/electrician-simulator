# 기관 LAN 학습 서비스 작업 기록

기준: `5b386e5`, `feature/qnet-all-wiring-capture`. 시작 시 미커밋 변경 없음.

## 요청 범위와 보존 원칙

- 기관 공용 PC 한 대에서 같은 LAN의 약 20명이 사용. 평일 7~8시간 운영.
- 실제 가입(아이디·비밀번호·닉네임만, 가입코드 없음), 로그인, 사용자별 데이터 보호.
- Q-Net 001~018 PDF 요구사항을 처음부터 대조하고 실제 결선 공통 엔진으로 검증.
- 결선 자동저장 구조 개선은 제외. 저장 완료 후 이동/종료, 동시 편집 금지 안내.
- Raspberry Pi Linux/ARM64 이전과 SQLite 백업/복원 준비.
- 기존 SQLite·닉네임 DB·사용자 답안 원본은 건드리지 않는다. 자동 계정 귀속 금지.
- LAN 실제 공개, 방화벽 변경, 기관 계정 생성은 수행하지 않는다.

## 단계

1. 기준 테스트, 실행 경로와 인증/저장 구조 확인.
2. 인증 모듈/API/화면과 사용자 분리 관련 테스트.
3. 18개 PDF 요구사항 재검수, 문제별 시나리오와 공통 엔진 관련 테스트.
4. 수업 시간에 해당하는 세션 수명/사용자 분리 검증, 배포·백업/복원 도구.
5. 실제 브라우저 확인, 전체 테스트, 최종 결과와 미확인 항목 기록.

## 현재 상태

- 2026-09-20 구현 및 로컬 검증 완료. 기관 LAN 실제 공개와 Pi 실기기 시험은 아직 수행하지 않음.
- 회원가입은 아이디·비밀번호·닉네임만 사용한다. 마지막 사용자 요청을 반영하여 가입코드를 UI/API/환경 설정/테스트에서 제거했다.
- LAN 모드는 인증을 강제하고 닉네임 또는 `X-User-Id` 요청값을 인증으로 신뢰하지 않는다. 기존 DB를 이름만으로 새 계정에 귀속하지 않는다.
- 계정·개인 결선을 함께 백업/복원해 같은 아이디·비밀번호·닉네임으로 다시 사용하는 테스트 통과. 복원본의 로그인 토큰만 폐기한다.
- 18개 문제의 요구사항 총 380개 확인점을 화면과 API에 제공한다. 당시 로컬 검수에서 PDF 논리망 증거 및 보완 사용자 후보 각각으로 전체 통과했다. 사용자 후보 결선이 포함된 상세 검수표는 공개 소스에서 제외하며, 현재 공개 검증 범위는 [최신 개발 상태](../DEVELOPMENT_STATUS.md)를 참고한다.
- 자체 시험용 localhost:8017, 별도 임시 DB에서 가입/로그아웃/계정 분리, 001의 실제 버튼 조작과 87개 결선 보존 확인. 운영 DB는 변경하지 않았다.

## 실제 변경 파일과 역할

- `backend/app/core/auth.py`, `auth_middleware.py`, `backend/app/api/auth.py`: 계정·비밀번호 해시·로그인·세션·CSRF·시도 제한.
- `backend/app/core/config.py`, `user_context.py`, `backend/app/main.py`: LAN 인증 강제, 사용자별 DB 선택, 인증 오류에서 입력 비밀번호 비노출.
- `frontend/src/components/AccountGate.tsx`, `features/user/authSession.ts`, `userProfile.ts`, `main.tsx`, `App.tsx`, `api/client.ts`: 가입/로그인/로그아웃, 계정별 요청, 이전 계정 탭 차단, 인증 사용자의 개인 분석 초안을 디스크 localStorage에 남기지 않음.
- `frontend/src/features/circuit/circuitDraft.ts`, `pages/CircuitAnalysisPage.tsx`: 인증 사용자 초안 저장 경로 적용.
- `backend/app/services/qnet_requirements.py`, `backend/app/api/operation.py`, `frontend/src/pages/OperationTestPage.tsx`: 18문제 요구 동작 목록/순서·독립 엔진 검사. 미저장 작업공간 안내를 잘못된 ‘기구 배치 없음’ 안내와 구분.
- `backend/app/simulation/engine.py`, `manager.py`: SS 중간 단선 계산, 동시 조작 직렬화, 계정별 메모리 동작 세션 수/수명 제한.
- `frontend/src/pages/WiringPage.tsx`, `PlaceholderPage.tsx`, `styles/global.css`: 저장 주의사항, JSON 가져오기 재시도 후 잘못 남은 오류 안내 제거, 신규 계정 문제 선택 안내, 계정 화면 스타일.
- `scripts/qnet_candidate_repairs_20260920.py`, `docs/private/data/engine-audit-corrected-2026-09-20/*.json`: 011·012·013 변환 후보의 별도 보완 사본과 재현 함수. 기존 원본 보존.
- `scripts/run_service.py`, `scripts/service_data.py`, `deploy/lan.env.example`, `deploy/electrician.service.example`, `backend/requirements-web.txt`, `backend/requirements.txt`: 웹 전용 실행·TLS 옵션·오프라인 DB 백업/안전 복원·운영자 비밀번호 재설정·Pi systemd 샘플.
- 추가 테스트: `test_lan_accounts.py`, `test_service_data.py`, `test_qnet_reviewed_requirements.py`, `AccountGate.test.tsx`, `StudyEntry.test.tsx`. 기존 문제 API/시퀀스 테스트 5개 파일도 신규 동작 시나리오와 연습 시간에 맞게 갱신.
- `README.md`, 이 문서, 운영 안내, 18문제 검수표: 최신 상태 및 남은 실환경 검증 기록.

## 실행한 테스트

기준 전체 테스트: Python 452개, frontend 107개 통과. 아래 값은 초기 LAN 구현(커밋 `3682852`)에서 가입코드 제거와 추가 안내 수정까지 반영한 결과다. 이후 USB 이동용 저장 경로 변경 결과는 문서 아래에 별도로 기록한다.

| 명령 (저장소 루트 기준, npm은 frontend에서 실행) | 최종 결과 |
|---|---|
| `.venv\Scripts\python.exe -X utf8 -m pytest backend/tests -o addopts='' -q --basetemp <새 임시 폴더>` | **542 passed**, 232.03초 |
| `npm test` | **111 passed**, 16파일 |
| `npm run typecheck` | 통과 |
| `npm run build` | 통과, dist는 이 명령으로 생성 |
| `.venv\Scripts\python.exe -X utf8 scripts/validate_problems.py` | 정상 23, 제외 0, 오류 0, 경고 19 |
| `git diff --check` | 통과 |

부분 검사도 수정 사이에 실행했다: 계정/백업 15개(후속 설정 테스트 1개 추가 후 전체 재실행), 신규 요구사항+010 기존 검증 114개, 가입/학습 진입 frontend 4개 통과. 기존 PDF 기구 모델 937관찰점은 전체 pytest 내부 회귀 검사로 포함된다.

Python 경고 1개는 Starlette TestClient의 httpx 사용 deprecation이다. 문제 패키지 경고 19개는 정답 검증 `unverified` 유지에 따른 경고다. 정상 동작 확인을 공식 채점 정답 승격으로 처리하지 않았다.

## 다중 사용자·수업 시간 검증의 정확한 범위

- 20개 계정의 동시 작업에서 계정당 5회 분석 저장/읽기·결선 저장/읽기, 총 400개 API 요청의 사용자 격리 확인.
- 시계를 진행시켜 8시간 활동 세션 및 30분 유휴/10시간 절대 만료 확인. 실제 8시간 경과 시험은 아니다.
- 백업/복원 후 실제 앱 API 로그인, 동일 계정 ID 및 저장된 workspace/결선 유지 확인.
- 시험용 브라우저에서 코드 없는 신규 가입, 기존 계정 재로그인, 다른 계정의 동일 URL 접근 차단, 001 동작 7묶음/21확인점 충족.

## 인계와 미완료 운영 항목

운영 절차는 [LAN 운영·Pi 이전 안내](lan-classroom-service.md)에 정리했다. 실제 기관 IP/허용 대역·HTTPS 인증서·OS 사용자 권한·방화벽은 담당자와 확인 후 설정해야 한다. 이 작업은 인터넷 포트 공개, 기관 계정 생성, 실데이터 이동/삭제, Pi 원격 설치, 클라우드 백업 연결을 하지 않았다.

실제 교실 20PC와 7~8시간 사용, Pi ARM64 성능, HTTPS 인증서 신뢰는 아직 미검증이다. 오프라인/동시 편집 충돌 복구 기능도 이번 범위 밖이다. ‘사용자 주의’ 안내가 소프트웨어 오류를 면책하거나 저장을 보장한다는 뜻은 아니다.

Git: 시작 커밋 `5b386e5`, 작업 브랜치 유지. 기능 변경은 전체 검증 후 로컬 커밋하며 원격 push는 하지 않는다. 최종 커밋 ID는 완료 응답과 `git log -1`에서 확인한다. ZIP은 이번 요청에 포함되지 않아 생성하지 않았다.

## 후속 변경: 프로그램 폴더 내 저장·USB 이동

2026-09-20 추가 요청, 기준 커밋 `3682852`.

- LAN/인증 서비스의 기본 저장 위치를 `프로그램/user-data/`로 변경. `ELECTRICIAN_DATA_DIR=user-data`는 실행 CWD가 아닌 프로그램 기준으로 해석하므로 드라이브 문자/폴더 위치 변경에 대응한다.
- 계정 DB와 `users/<계정ID>.db`를 함께 보관. 사용자 PC마다 저장하는 방식이 아니라 서버 프로그램 폴더에 통합 저장한다.
- 기존 절대 경로 지정은 계속 지원한다. 인증 없는 기존 데스크톱 경로와 원본 DB는 자동 이동·삭제하지 않았다.
- 계정 데이터를 정적 공개 폴더 안에 설정하면 시작을 거부한다. `user-data`, 운영 설정·백업 폴더는 Git에서 제외했다.
- 서비스 실행 시 실제 데이터 경로를 표시하며, Windows 설정 예시와 Pi systemd 쓰기 허용 폴더도 프로그램 내 저장 방식에 맞췄다.
- 임시 계정/결선을 만든 뒤 서버를 종료하고 프로그램 폴더를 복사, 다른 CWD에서 같은 계정 로그인·결선 로딩 성공. 실제 운영 데이터가 아닌 임시 데이터만 사용했다.
- 관련 테스트 18개 통과(이식 경로/런처/정적 폴더 차단/복사 후 로그인 + 기존 백업·설정 검사).
- 최종 전체: `python -X utf8 -m pytest backend/tests -o addopts='' -q --basetemp <새 임시 폴더>` **552 passed**, 233.43초, 기존 deprecation 경고 1개. `npm test` **111 passed**, `npm run typecheck`, `npm run build` 통과.
- `scripts/validate_problems.py`: 정상 23, 오류 0, 기존 unverified 경고 19. `git diff --check` 통과. `git check-ignore`로 데이터/설정 비포함 확인.
- 기존 실제 DB 3개(`data/dev`, `data/ui-simulation`, `%LOCALAPPDATA%/ElectricianSimulator`)의 크기·최종 수정 시각이 작업 전후 동일함을 확인했다. 기존 절대 경로의 운영 계정 DB를 자동으로 이동시키는 작업은 수행하지 않았다.

## 후속 변경: 계정 화면 문구·비밀번호 최소 길이

2026-09-20 추가 요청, 기준 커밋 `dd0af43`.

- 로그인/가입 화면의 ‘기관 LAN 학습 서비스’, 서버 이전 안내, 아이디/비밀번호 입력창 예시를 제거했다. 소개는 ‘개인 계정으로 학습 기록을 저장합니다.’, 하단 안내는 관리자 비밀번호 재설정 문장만 남겼다.
- 가입 화면, 가입 API, 관리자 재설정 CLI의 비밀번호 범위를 6~128자로 통일했다. 기존 계정의 비밀번호 해시·기록은 변경하지 않았다.
- 관련 Python 테스트 22개 및 계정 화면 테스트 3개 통과. 6자 가입/재로그인/재설정 성공, 5자·129자 거부, 재설정 시 기존 세션 폐기, 오류 응답의 비밀번호 비노출을 확인했다.
- 전체 `python -X utf8 -m pytest backend/tests -o addopts='' -q --basetemp <새 임시 폴더>`: **558 passed**, 250.74초, 기존 deprecation 경고 1개.
- `npm test`: **111 passed**, `npm run typecheck`, `npm run build` 통과. `scripts/validate_problems.py`: 정상 23, 오류 0, 기존 unverified 경고 19. `git diff --check` 통과.
- 별도 임시 데이터의 localhost:8018에서 로그인/가입 화면을 직접 확인했다. 가입 비밀번호 입력의 `minlength=6`, 두 입력창의 placeholder 제거 및 문구/배치 확인. 실제 계정 생성·데이터 변경 없이 시험용 탭과 서버를 종료했다.
- 이미 실행 중인 서비스에는 서버 재시작과 브라우저 새로고침이 필요하다. 실제 서비스의 재시작이나 LAN 공개는 이 작업에서 수행하지 않았다.
