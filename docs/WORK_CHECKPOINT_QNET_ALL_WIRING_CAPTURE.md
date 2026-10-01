# Q-Net 001~018 결선 저장 작업 체크포인트

갱신: 2026-08-28

## 완료된 기준

- 브랜치: `feature/qnet-all-wiring-capture`
- 시작 HEAD: `628b92c38fee5a9787159c7996aef8ccae6dbfbc`
- 수정 전 전체 기준: Python 224 passed, 문제 23개/오류 0/의도된 경고 19, frontend 71 passed, TypeScript PASS, Vite 64 modules.
- 비공개 Q018 후보 감사 자료는 `628b92c`에 별도 보존되어 있으며 공개 API·번들·ZIP에서 제외해야 한다.

## 현재 구현 완료

- DB schema 12: 기존 `practice_wiring_drafts` 추가형 컬럼 및 `practice_wiring_snapshots` 테이블.
- 사용자 답안 전용 모델: 오결선·자기결선·중복선을 저장 가능한 capture 모델.
- 답안 독립 구조 경고: 문제 밖 단자, 비활성 단자, 자기 연결, 중복, 수용량, 명확한 안전 경고.
- 작업공간 생성/목록, draft 저장/조회/삭제, 스냅샷 생성/목록/복제, 안전 JSON export/import API.
- Q-Net 001~018의 공개 board가 있으면 결선 작성 허용. 미구현 엔진은 활성화하지 않음.
- 사용자/프로필 격리는 기존 사용자별 SQLite pool을 그대로 사용.
- 프런트 작업공간/스냅샷/export/import/자동저장 상태/구조 경고/엔진 대기 UI.
- 008·010·018은 선택한 작업공간 ID를 동작시험으로 전달.

## 통과한 부분 테스트

- Backend focused: 39 passed
  - `backend/tests/test_qnet_all_wiring_capture.py`
  - `backend/tests/test_wiring_api.py`
  - `backend/tests/test_qnet_008_018_public_practice.py`
  - `backend/tests/test_database.py`
- Frontend: TypeScript PASS, Vitest 7 files / 71 tests PASS (UI mock 갱신 후).

## 완료된 검증

- 전체 Python: 245 passed, 실패 0, 기존 deprecation warning 1.
- 문제 검사기: 23 loaded, 오류 0, 의도된 draft 경고 19, Q-Net 18/18.
- 프런트: 7 files / 72 passed, TypeScript PASS, Vite 64 modules.
- 브라우저: 자동저장·새로고침/서버 재시작 복원·구조 경고·390px UI 확인.
- Q001은 결선 저장 전용, Q008·010·018은 선택 workspace로 기존 동작시험 진입 확인.
- 배포 스크립트는 Q-Net 001~018 전체 answer 복사본의 정답·채점 필드를 제거한다.

## 남은 마감 절차

1. 변경사항 커밋.
2. 전체 ZIP 생성 및 압축 해제본 smoke 검사.
3. SHA-256과 최종 Git 상태 기록.

## 주의사항

- `frontend/dist`를 직접 수정하지 말고 `npm run build`만 사용한다.
- 테스트 데이터는 `D:\project\elec\qnet-18` 아래 별도 디렉터리를 사용한다.
- 비공개 후보·`docs/private`·비공개 테스트를 ZIP에 넣지 않는다.
- push/tag/amend 금지. 기존 SQLite와 자유회로 데이터를 삭제하지 않는다.
