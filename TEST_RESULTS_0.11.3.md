# 0.11.3 자동 검증 결과

검증일: 2026-08-22  
대상 버전: 0.11.3

## 프로젝트 기준 상태

- 프로젝트는 Git 저장소가 아니므로 작업 전 소스 파일의 SHA-256을 기록한 뒤 작업 후 해시와 비교했다.
- `.venv`, `node_modules`, `frontend/dist`, 캐시, 로그, DB와 사용자 데이터는 기준 변경 파일 계산에서 제외했다.
- 기존 자유회로 저장 API와 SQLite 스키마를 재사용했으며 DB 마이그레이션은 추가하지 않았다.

## 자동 테스트

| 검사 | 실행 방법 | 결과 |
|---|---|---|
| 백엔드·데스크톱 | `.venv/bin/python -m pytest backend/tests desktop/tests -q` | 137개 통과 |
| 프런트엔드 | `node node_modules/vitest/vitest.mjs run` | 7개 파일, 63개 통과 |
| TypeScript | `node node_modules/typescript/bin/tsc -b --pretty false` | 통과 |
| React 운영 빌드 | `node node_modules/vite/bin/vite.js build` | 63개 모듈, 성공 |
| 실제 결선 데모 | `.venv/bin/python scripts/run_actual_wiring_demo.py` | 모든 항목 통과 |
| 통합 기본보드 데모 | `.venv/bin/python scripts/run_basic_board_demo.py` | 모든 항목 통과 |
| 문제 데이터 검사 | `.venv/bin/python scripts/validate_problems.py` | 정상 5, 제외 0, 오류 0, 경고 1 |

Python 테스트에는 기존 `StarletteDeprecationWarning` 1건이 남아 있다. 기능 실패는 아니며 테스트 결과를 숨기지 않았다.

## 0.11.3 핵심 자동 확인

- 자유회로에서 선택 전선 Delete 키 삭제
- 입력·선택 요소에 포커스가 있을 때 Delete 키 보호
- Delete 삭제 뒤 Undo 복원
- 빠른 연속 편집을 0.8초 debounce로 한 번 저장
- 초기 작업공간 로드를 사용자 편집으로 오인하지 않음
- 저장 실패 뒤 로컬 전선 유지와 수동 재시도
- 동작시험 진입 전에 최신 결선 저장 완료
- 겹친 저장 요청의 순차 처리와 최신 revision 저장
- 제어함·동작시험·자유회로의 확대·축소 버튼 제거
- 전체 회로도 분석 화면의 확대 기능 유지
- 결선 참고 회로도의 버튼 제거와 읽기 전용 표시 유지
- 왼쪽 문제 정보 카드 제거와 상단 현재 문제 표시 유지
- 기존 그래픽·요약·외부선·TB 연결 표시 회귀

## 운영 빌드

```text
frontend/dist/index.html                   0.48 kB
frontend/dist/assets/index--9bDnFkN.css   40.68 kB
frontend/dist/assets/index-BMWcA_B6.js   325.06 kB
```

## 문제 데이터 상태

```text
[정상] training_socket_demo_001
[정상] operation_demo_001
[정상] eocr_sequence_demo_001
[정상] forward_reverse_interlock_demo_001
[정상] practice_001
[경고] answer.json (verification.status): 정답이 아직 검증되지 않았습니다.
[정책 경고] 검증된 Q-Net 공개문제 데이터가 없습니다: 0/18
```

0.11.3에서는 문제 데이터와 전기 동작 정의를 변경하지 않았다.

## 수동 확인이 필요한 항목

- 실제 Windows pywebview 창에서 1366×768·1920×1080·최대화 레이아웃
- 오른쪽 패널의 실제 글자 가독성
- 창 크기 변경 뒤 보드·전선·단자 위치 일치
- 정상 종료와 강제 종료 직전 자동저장 차이
- 기존 사용자 DB와 자유회로 작업공간 복원

상세 순서는 `docs/ui-manual-test-0.11.3.md`를 따른다.

## 확인된 제한사항

- 브라우저나 프로세스를 강제 종료하면 진행 중인 비동기 저장 완료를 보장할 수 없다. `자동 저장됨`을 확인하거나 수동 저장 후 종료한다.
- 실제 Windows 장치 환경은 현재 Linux 검증 환경에서 직접 실행하지 못했으며 데스크톱 런처 자동 테스트로 확인했다.
- 검증된 Q-Net 공식 공개문제 데이터는 기존과 동일하게 0/18이다.
- 빈 보드 기구 팔레트와 기구 자유 배치는 0.12.0 이후 범위다.
