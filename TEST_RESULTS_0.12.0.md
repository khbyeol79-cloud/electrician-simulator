# 0.12.0 자동 검증 결과

대상: 0.11.3 기존 프로젝트에 0.12.0 빈보드·기구 팔레트 증분 변경 적용

## 프로젝트 조사

- 시작 버전: 0.11.3
- 공개 신규 자유회로 템플릿: 기본보드 1종
- 과거 자유회로 템플릿: 신규 목록에서 숨김, 기존 API/저장 호환 유지
- 실제 결선 엔진: `DeviceInstanceFactory` → `DeviceBehaviorRuntimeComposer` → `OperationEngine`
- SQLite 시작 스키마: 8, 사용자별 DB 및 `workspace_id` 분리
- Q-Net 검증 문제: 현재 프로젝트에 0/18. 이번 버전에서 문제 데이터를 생성·수정하지 않음

## 구현 검증

- 시작 보드: `basic_board_001`, `empty_board_001` 두 개만 공개
- 빈보드: TB5·TB6만 고정, 기존 좌표계·통로 유지
- 팔레트: 내부 6종, 외부 8종, 카탈로그 검증 상태와 capability 공개
- 조립 원본: nullable `assembly_json`, 기존 레코드는 변환하지 않음
- 구성기: 설치 기구에서 보드·회로·동작·외부 단자·소켓 배치를 서버 재구성
- 배치: 내부 상·하단 5칸, 외부 상·하단 10칸 그리드
- 편집: 설치·이동·삭제·타이머 지연 설정, 기구·전선 통합 Undo/Redo, 자동저장
- 동작시험: 전원 미설치 차단, 설치 후 기존 공통 엔진 사용
- 정답 비노출: 팔레트·자유회로 API에 answer/expected_nets 없음
- Windows DB 정리: 모든 저장소 트랜잭션 종료 시 SQLite 연결과 파일 핸들을 즉시 닫음
- 임시 DB 회귀 검사: 컨텍스트 종료 후 닫힌 연결 확인 및 DB 파일 즉시 삭제 확인
- 빈보드 경로: 설치 기구 단자를 금지영역 안에 가두지 않으며 기존 확대 금지영역 작업공간도 결선 가능

## 실행 결과

1. `.venv/bin/python -m pytest backend/tests desktop/tests`
   - 140 passed, 1 warning
   - 경고: FastAPI TestClient의 Starlette/httpx deprecation 경고
2. `frontend/node_modules/.bin/vitest run`
   - 7 files passed, 65 tests passed
3. `frontend/node_modules/.bin/tsc --noEmit`
   - 통과
4. `frontend/node_modules/.bin/vite build`
   - 63 modules transformed, production build 성공
5. `.venv/bin/python scripts/validate_problems.py`
   - 정상 5개, 제외 0개, 오류 0개, 경고 1개
   - 정책 경고: 검증된 Q-Net 공개문제 0/18
6. `.venv/bin/python scripts/run_actual_wiring_demo.py`
   - 자기유지·모터 상 순서·STOP·EOCR 항목 모두 통과
7. `.venv/bin/python scripts/run_basic_board_demo.py`
   - 20개 기본보드 실제 결선 항목 모두 통과
8. `.venv/bin/python scripts/run_empty_board_demo.py`
   - 템플릿·팔레트·빈보드·릴레이·전원·공통 엔진 6개 항목 모두 통과

## 실행환경 확인 범위

- Web: FastAPI API와 React 정적 파일 테스트 통과
- Desktop: 로컬 서버/포트/런처 자동 테스트 포함 Python 140개 통과
- Windows 임시 DB: 기본보드·빈보드 데모가 앱 종료와 임시 폴더 정리까지 완료되도록 연결 수명 수정
- Offline: 외부 CDN·외부 API 없이 로컬 카탈로그·문제·SQLite·`frontend/dist` 사용
- 실제 Windows pywebview 창: 현재 Linux 개발 환경에서는 직접 실행하지 못함. Windows에서 `run_desktop.bat` 수동 확인 필요

## 알려진 제한

- MC 12P, EOCR 12P, NC Limit Switch는 카탈로그 상태가 `unverified`이며 UI에도 교육용·미검증으로 표시한다.
- X 릴레이와 T 타이머는 카탈로그에 검증된 일부 코일·접점만 사용하며 나머지 핀 기능을 추측하지 않는다.
- 픽셀 단위 자유 배치, 여러 독립 전원, 실제 전압·전류·발열·차단전류는 구현 범위가 아니다.
- 사용자가 직접 만든 기구 동작 정의 편집과 Q-Net 18문제 데이터 제작은 이번 버전에 포함하지 않는다.
