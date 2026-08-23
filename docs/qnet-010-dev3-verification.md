# Q-Net 010 검증 기록 — 0.14.0-dev3

## 이번 단계에서 완료한 것

- 0.14.0-dev2-hotfix1의 FUSE 직접결선 모델을 유지한다.
- Q-Net 010 보드의 F는 한 기구이며 단자는 F-1, F-2, F-3, F-4 네 개다.
- 내부 독립 도통은 1-2와 3-4이다.
- 실행 배포본 WiringBoard 렌더러에 F 전용 2열 퓨즈홀더 그래픽을 추가했다.
- 위쪽 1·3, 아래쪽 2·4 wire endpoint는 기존 board 좌표를 그대로 사용한다.
- F 라벨을 작은 중앙 라벨로 축소해 두 퓨즈 카트리지를 가리지 않게 했다.
- hotfix 이후 `pin_number=null`인 직접결선 FUSE를 readiness 검사기가 정상 PASS하도록 수정했다.

## 중요한 소스 제약

현재 전달받은 증분 자료에는 `frontend/src/features/wiring/components/WiringBoard.tsx` 원본이 포함되어 있지 않다. 따라서 이번 dev3의 실제형 FUSE 디자인은 현재 실행되는 `frontend/dist` 배포 번들에 반영했다.

사용자 PC에서 이후 `npm run build`를 수행하면 전체 소스의 기존 WiringBoard 구현으로 dist가 다시 생성되어 이번 배포번들 디자인 변경이 사라질 수 있다. 정식 0.14.0 전에 전체 프로젝트 소스를 기준으로 동일 렌더링을 원본 `WiringBoard.tsx`에도 반영해야 한다.

## 이번 단계에서 계속 차단한 것

다음 항목은 공식 근거 및 전체 엔진 소스가 충분하지 않아 추측해서 작성하지 않았다.

- 010 구조화 circuit
- 010 expected_nets
- 010 allowed_alternatives
- TB equivalent groups
- 010 공개 operation
- 010 operation_tests
- grading/operation API guard 변경
- 010 verified 승격

현재 010은 계속 `draft/unverified`가 맞다.
