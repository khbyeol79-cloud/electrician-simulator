# 0.11.2 자동 검증 결과

검증 기준일: 2026-08-22  
기준 버전: 0.11.1  
대상 버전: 0.11.2

## 실행 결과

| 구분 | 실행 명령 | 결과 |
|---|---|---|
| Python 백엔드·Desktop | `.venv/bin/python -m pytest backend/tests desktop/tests -q` | 137개 통과, 실패 0개 |
| 프런트엔드 | `frontend/node_modules/.bin/vitest run` | 6개 파일, 57개 통과 |
| TypeScript | `frontend/node_modules/.bin/tsc -b` | 통과 |
| React 운영 빌드 | `frontend/node_modules/.bin/vite build` | 62개 모듈, 성공 |
| 문제 데이터 | `.venv/bin/python scripts/validate_problems.py` | 정상 5개, 제외 0개, 오류 0개, 경고 1개 |
| 기존 실제결선 데모 | `.venv/bin/python scripts/run_actual_wiring_demo.py` | 전 항목 통과 |
| 신규 기본보드 데모 | `.venv/bin/python scripts/run_basic_board_demo.py` | 20개 확인 항목 통과 |
| 패치 적용 복사본 | 0.9.4 전체본부터 후속 패치를 순서대로 적용한 0.11.1 복사본에 0.11.2 패치 적용 | 버전 0.11.2, Python 137개와 기본보드 데모 통과 |

문제 검사기의 경고 1개는 `practice_001` 답안 미검증 경고다. 공식 검증 Q-Net 문제는 기존 정책과 동일하게 `0/18`이며 이번 버전에서 문제 데이터를 임의로 추가하지 않았다.

## 0.11.2 핵심 자동 확인

- 신규 생성용 템플릿 API는 `basic_board_001` 하나만 노출한다.
- 기본보드는 Q-Net·자체제작 문제 목록에 추가되지 않는다.
- 기본보드에는 답안, `expected_nets`, 초기 전선이 없다.
- 이름만 전송하면 서버가 서로 다른 `fc_...` workspace ID를 생성한다.
- 기존 3종 템플릿의 명시적 ID 호환 API는 유지한다.
- 기존 SQLite 자유회로 JSON 구조를 변경하지 않는다.
- 카탈로그 구성 후 X1·X2·T1·T2·MC1·MC2 코일과 동적 접점 참조가 유효하다.
- X1 단독 여자·복귀, X1 NO 자기유지, PB0 STOP이 실제 결선으로 동작한다.
- T1 ON-delay 전 GL OFF, 1,000ms 뒤 GL ON이 확인됐다.
- MC1 주접점, 정상 상순서 정회전, 두 상 교환 역회전, 한 상 누락 결상이 확인됐다.
- 상대 MC의 실제 NC 접점이 반대 코일을 차단한다.
- EOCR 95-96 트립, 97-98 RL 경보, 복귀 후 새 START 필요가 확인됐다.
- EOCR 95-96 우회 시 코일을 메타데이터로 강제 정지하지 않고 보호 우회 위험을 표시한다.
- 수동 시험 문서의 60개 결선 행이 실제 기본보드·외부기구·런타임 단자 ID만 참조하는지 검사한다.
- 프런트엔드 신규 화면에 템플릿 드롭다운·workspace ID 입력란이 없고 raw template ID 대신 읽을 수 있는 이름을 표시한다.

## 운영 빌드

생성 파일:

- `frontend/dist/index.html`
- `frontend/dist/assets/index-BUK8lGZO.css`
- `frontend/dist/assets/index-DY3_tYgr.js`

Node.js는 개발·재빌드에만 사용한다. 패치에는 위 운영 빌드가 포함되므로 일반 Desktop/Web 사용자는 Node.js 없이 실행할 수 있다.

## 직접 확인이 필요한 환경

다음 항목은 자동 테스트로 구조를 확인했지만 이 Linux 작업 환경에서 실제 Windows 장치로 실행하지 않았다.

- Windows pywebview·WebView2 창 실행
- 완전 인터넷 차단 상태의 Desktop 실행
- `run_web.bat -Lan`과 실제 스마트폰·태블릿 접속
- 서로 다른 실제 브라우저에서 사용자 작업공간·동작 세션 분리
- 화면 크기별 외부선 영역과 TB 좌우 포트의 시각적 위치

## 유지한 제한

- X1·X2는 검증된 코일 2-7과 NO 6-3만 포함한다. 나머지 8P 접점은 추측하지 않았다.
- T1·T2는 코일 2-7과 ON-delay NO 1-3을 포함한다.
- MC·EOCR·LS2 교육용 정의는 기존 `unverified` 상태를 유지한다.
- 실제 전압·전류·단락전류·접촉저항·RPM·토크는 계산하지 않는다.
- 빈보드·기구 팔레트·기구 설치·삭제·자유배치는 0.12.0 범위다.
