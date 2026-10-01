# Q-Net 공개문제 001~018 제어함 기구 배치 재검수

- 검수일: 2026-09-05
- 공식 근거: HRDK 공개문제 각 PDF 6쪽 `2) 제어판 내부 기구 배치도`
- 범위: 내부 기구 종류, 위·아래 행, 좌우 순서, 베이스 유형, FUSE, TB5/TB6, 렌더링 충돌
- 제외: 회로 정답, expected_nets, 사용자 결선 후보, 동작 시나리오

## 검수 결과

| 문제 | PDF 6쪽 위 행 | PDF 6쪽 아래 행 | 수정 전 확인사항 | 결과 |
|---|---|---|---|---|
| 001 | F, EOCR, MCCB, X, FR | T, FLS, MC1, MC2 | 순서 일치, 아래 행 8P row 메타데이터와 금지영역 불일치 | 수정·검증 완료 |
| 002 | EOCR, MCCB, F, X, FR | MC1, MC2, T, FLS | 순서 일치, 아래 행 8P row 메타데이터 불일치 | 수정·검증 완료 |
| 003 | MCCB, EOCR, F, X, FR | T, FLS, MC1, MC2 | F-X-FR 순서 일치, 아래 행 8P row 메타데이터 불일치 | 수정·검증 완료 |
| 004 | MCCB, EOCR, FR, X, F | FLS, MC1, MC2, T | 순서 일치, 아래 행 8P row 메타데이터와 금지영역 불일치 | 수정·검증 완료 |
| 005 | EOCR, F, MCCB, FR, X | MC1, MC2, FLS, T | 순서 일치, 아래 행 8P row 메타데이터와 금지영역 불일치 | 수정·검증 완료 |
| 006 | EOCR, MCCB, F, X, FR | FLS, T, MC1, MC2 | 순서 일치, 아래 행 8P row 메타데이터와 금지영역 불일치 | 수정·검증 완료 |
| 007 | MCCB, F, EOCR, FR, X | FLS, T, MC1, MC2 | 순서 일치, 아래 행 8P row 메타데이터와 금지영역 불일치 | 수정·검증 완료 |
| 008 | F, MCCB, EOCR, X, FR | T, MC1, MC2, FLS | 순서 일치, 아래 행 8P row 메타데이터와 금지영역 불일치 | 수정·기능 회귀 검증 완료 |
| 009 | MCCB, EOCR, F, FR, X | T, MC1, MC2, FLS | 순서 일치, 아래 행 8P row 메타데이터와 금지영역 불일치 | 수정·검증 완료 |
| 010 | MCCB, EOCR, X2, X1, F | T1, T2, MC1, MC2 | 순서 일치, 아래 행 8P row 메타데이터와 금지영역 불일치 | 수정·기능 회귀 검증 완료 |
| 011 | EOCR, MCCB, F, X2, X1 | MC1, MC2, T2, T1 | 순서 일치, 아래 행 8P row 메타데이터와 금지영역 불일치 | 수정·검증 완료 |
| 012 | F, MCCB, EOCR, X1, X2 | T2, T1, MC1, MC2 | 순서 일치, 아래 행 8P row 메타데이터와 금지영역 불일치 | 수정·검증 완료 |
| 013 | EOCR, MCCB, F, X1, X2 | T1, MC1, MC2, T2 | 순서 일치, 아래 행 8P row 메타데이터와 금지영역 불일치 | 수정·검증 완료 |
| 014 | F, MCCB, EOCR, X2, X1 | T2, T1, MC1, MC2 | 순서 일치, 아래 행 8P row 메타데이터와 금지영역 불일치 | 수정·검증 완료 |
| 015 | MCCB, EOCR, F, X2, X1 | T2, MC1, MC2, T1 | 순서 일치, 아래 행 8P row 메타데이터와 금지영역 불일치 | 수정·검증 완료 |
| 016 | MCCB, EOCR, X1, X2, F | T2, MC1, MC2, T1 | 순서 일치, 아래 행 8P row 메타데이터와 금지영역 불일치 | 수정·검증 완료 |
| 017 | MCCB, F, EOCR, X1, X2 | T1, MC1, MC2, T2 | 순서 일치, 아래 행 8P row 메타데이터와 금지영역 불일치 | 수정·검증 완료 |
| 018 | MCCB, EOCR, F, X1, X2 | T2, MC1, MC2, T1 | 순서 일치, 아래 행 8P row 메타데이터와 금지영역 불일치 | 수정·기능 회귀 검증 완료 |

## 실제 수정

1. 아래 행의 모든 기구를 `row: 2`로 정규화했다. 기존 생성기는 8P 템플릿의 `row: 1`을 복사하여 같은 물리 행의 기구가 서로 다른 행으로 기록됐다.
2. 001 및 004~018의 `forbidden_areas`를 실제 렌더링 기구 ID·좌표·크기에 맞춰 다시 생성했다. 002·003은 이전 보강에서 이미 동기화되어 있었다.
3. 보드 전용 안전 동기화 옵션 `--boards-only`를 추가했다. 이 옵션은 problem.json, answer.json, operation 정의를 건드리지 않는다.
4. 전체 패키지 재생성은 `--force` 없이는 중단되도록 보호했다.
5. PDF 6쪽 순서, 행, 충돌, 단자 ID 유일성, 금지영역 동기화를 001~018 전체 자동 테스트로 고정했다.

## 기구 형태와 단자 확인

- F: 단일 몸체의 4단자·2독립회로, 단자 `1-2` 및 `3-4`
- X/X1/X2, T/T1/T2, FLS, FR: 8P 베이스
- EOCR, MC1, MC2: 12P 베이스
- MCCB: L1/L2/L3 및 T1/T2/T3
- TB5: 위쪽, TB6: 아래쪽, 각 10P+10P

## 수동 확인

운영 프런트엔드를 로컬 FastAPI에 연결하고 Q-Net 001~018의 제어함 결선 화면을 각각 열어 확인했다. 모든 화면에서 PDF 6쪽과 동일한 행별 순서가 표시됐고 기구 몸체·라벨·단자 간 겹침은 발견되지 않았다. 검수 서버는 임시 데이터 경로를 사용하여 기존 SQLite와 사용자 작업공간을 변경하지 않았다.

## 미확정 사항

배치도 자체에는 미확정 항목이 없다. 회로 접점 번호, 사용자 결선 답안, 동작 요구사항은 이번 검수 범위가 아니며 기존 검증 상태를 유지한다.

## 검증 명령과 결과

- `python -m pytest backend/tests/test_qnet_public_sources.py backend/tests/test_qnet_all_wiring_capture.py backend/tests/test_qnet_008_special_devices.py backend/tests/test_qnet_008_018_public_practice.py backend/tests/test_qnet_010_fuse_board.py backend/tests/test_qnet_010_private_validation.py -q`: 151개 통과
- `python -m pytest -q`: 전체 336개 통과
- `python scripts/validate_problems.py`: 23개 패키지, 오류 0, 경고 19
- `python -m tools.validate_problem --all`: 23개 패키지, 오류 0, 경고 19
- `npm test -- --run`: 7개 파일, 73개 테스트 통과
- `npm run typecheck`: 통과
- `npm run build`: 64개 모듈 production build 통과
- `git diff --check`: 통과

19개 경고는 기존 Q-Net 공개문제 답안의 `unverified` 상태이며 이번 배치 수정으로 새로 발생한 오류가 아니다.
