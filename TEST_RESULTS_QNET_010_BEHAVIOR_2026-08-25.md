# Q-Net 010 동작 검증 개발 테스트 결과 (2026-08-25)

## 대상

- 기준 커밋: `7a17cf3af361157d06535158b3a71ba306de6fbe`
- 작업 브랜치: `feature/qnet-010-behavior-validation`
- 범위: Q-Net 공개문제 010, 공통 4단자 FUSE, 개인 분석 메모, 실제 결선 동작 요구사항
- 제외: Q-Net 001~009·011~018 기능 구현, 공개 합격/불합격 및 점수 채점

## 자동 테스트

| 명령 | 결과 |
|---|---:|
| `.venv\Scripts\python.exe -m pytest backend/tests -q --basetemp D:\project\elec\qnet-18\pytest-release-20260825 -p no:cacheprovider` | 199 passed, 경고 1(Starlette/httpx 사용 중단 예고) |
| `.venv\Scripts\python.exe scripts/validate_problems.py` | 23 패키지, 오류 0, 제외 0, 경고 19 |
| `npm run typecheck` (`frontend`) | 통과 |
| `npm test -- --run` (`frontend`) | 7 files, 71 passed |
| `npm run build` (`frontend`) | 64 modules, 운영 번들 생성 |
| `.venv\Scripts\python.exe scripts/check_stable_fuse_build.py` | 통과 |
| `.venv\Scripts\python.exe scripts/run_basic_board_demo.py` | 통과 |
| `.venv\Scripts\python.exe scripts/run_empty_board_demo.py` | 통과 |
| `.venv\Scripts\python.exe scripts/run_actual_wiring_demo.py` | 통과 |
| `.venv\Scripts\python.exe scripts/run_qnet_18_smoke_test.py` | 통과 |
| `.venv\Scripts\python.exe scripts/check_qnet_010_readiness.py` | 19 통과, 1 근거 차단(의도된 종료코드 1) |

## 추가 회귀 범위

- 기존 2단자 FUSE 팔레트 비노출·신규 생성 거부, 기존 저장 형식 로드 호환
- 기본보드와 빈보드 신규 FUSE가 1-2·3-4 독립 4단자 모델인지 확인
- EOCR 95–97 내부 공통, A1–A2 실제 전원 인가 전 트립 거부, 운전 중 트립·수동 복귀
- 8P 전환접점 전체 그룹 교환과 TB 번호 변경의 전기적 동등성
- 정상·누락·오결선·단락·STOP/FUSE/EOCR/타이머/접점 우회
- 25개 공개 요구 동작: 정상 결선 전부 충족, 빈 결선 전부 미충족, 우회 결선의 관련 항목 미충족
- 분석 메모 사용자 격리·문제 버전 검사·자동저장·삭제
- 일반 문제 API, 동작 API, 프런트 소스/운영 번들에 `expected_nets`, `operation_tests`, 비공개 Net ID 비노출

## 최종 상태

기능 및 회귀 테스트는 통과했다. 단, Q-Net 공식 PDF가 FUSE 단자번호 `1-2 / 3-4`를 직접 명시하지 않으므로 문제와 비공개 답안은 `draft/unverified`를 유지한다. 공개 기능은 점수나 합격/불합격이 아닌 실제 결선 기반 `충족/미충족`만 제공한다.
