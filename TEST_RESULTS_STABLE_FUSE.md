# TEST RESULTS — 0.13.0 stable-fuse

## 범위
마지막 정상 실행 전체 소스를 기준으로 FUSE 디자인과 관련 회귀 테스트만 안정화했다. Q-Net 010의 채점/동작시험/엔진/API 로직은 변경하지 않았다.

## 결과 요약

| 검사 | 결과 |
| --- | --- |
| Backend 전체 pytest | **149 passed** |
| Q-Net 18개 smoke | **PASS (18/18)** |
| Q-Net 010 smoke | **PASS, draft/unverified 차단 유지** |
| Q-Net 010 readiness | **13 PASS / 5 BLOCKED (의도된 미검증 항목)** |
| FUSE 전용 안정화 검사 | **PASS** |
| Q-Net 010 package validator | **오류 0 / 경고 1 (unverified 경고만 존재)** |
| TypeScript/TSX syntax transpile | **35 files PASS** |
| 실행용 JS `node --check` | **PASS** |
| 실행용 bundle FUSE renderer/CSS | **PASS** |
| FastAPI full app startup/TestClient | **PASS** |
| Q-Net API 로딩 | **18/18** |

## FUSE 확인 결과
- `F` 기구 1개
- 단자 `1, 2, 3, 4`
- 내부 회로 `1 ↔ 2`, `3 ↔ 4`
- socket pin이 아닌 직접결선 단자: `pin_number = null`
- Q-Net 010 보드: 상단 `1/3`, 하단 `2/4`
- 원본 `frontend/src/.../WiringBoard.tsx`에 전용 2카트리지 renderer 존재
- 실행용 `frontend/dist`에도 동일 renderer와 CSS 존재
- 기존 `fuse_single_pole_training` 모델 유지

## 안정성 확인
원본 전체 소스 ZIP과 해시 비교하여 다음 핵심 실행/정답 파일은 이번 작업에서 변경하지 않았음을 확인했다.

- `backend/app/simulation/engine.py`
- `backend/app/api/operation.py`
- `backend/app/api/wiring.py`
- `backend/app/services/wiring_service.py`
- `problems/qnet_electrician_practical_010/answer.json`
- `problems/qnet_electrician_practical_010/problem.json`
- `problems/qnet_electrician_practical_010/manifest.json`
- `catalog/device_behaviors.json`

## Q-Net 010의 의도된 차단
다음 5개 항목은 아직 검증하지 않았으므로 계속 차단한다.

1. `circuit.definition_status = structure_only`
2. 공개 operation 정의 없음
3. `expected_nets = []`
4. `operation_tests = []`
5. `manifest = draft`, `answer.verification = unverified`

즉 이번 빌드에서는 Q-Net 010을 억지로 개방하지 않는다.

## Frontend build에 대한 주의
현재 샌드박스에는 완전한 `node_modules`가 없고 npm registry 접근도 시간 초과되어 `npm ci`/Vitest를 새로 실행하지 못했다.

대신 다음 방식으로 실행본을 검증했다.
- FUSE renderer 원본 TSX는 이전에 실제 번들 생성에 사용된 동일 renderer 소스와 일치
- 해당 소스에서 생성된 실행용 `frontend/dist`를 전체본에 동기화
- 표시 버전 fallback만 현재 0.13.0에 맞춤
- TS/TSX 35개 파일 TypeScript transpile 구문 검사 PASS
- 생성된 JS bundle `node --check` PASS
- JS/CSS bundle에 `dual-fuse-holder`, `dual-fuse-cartridge` 존재 확인
- FastAPI에서 실제 dist의 `index.html` 제공 PASS

사용자 PC에서 추후 `npm install` 후 `npm run build`를 실행해도 원본 `frontend/src`에 같은 FUSE renderer가 있으므로 디자인 수정이 사라지지 않는다.
