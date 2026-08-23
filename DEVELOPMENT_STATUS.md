# Development Status — stable-fuse

## 권장 기준
현재 권장 빌드는 **0.13.0 stable-fuse**다.

## 공식 Q-Net 문제
001~018은 모두 계속 `draft` 상태다. 이번 안정화 빌드에서는 어떤 공식문제도 `verified`로 승격하지 않았다.

## Q-Net 010
- 공식 회로 표시: 유지
- 8P relay/timer: 검증값 유지
- 12P MC/EOCR: 기존 검증값 유지
- FUSE: 1기구 / 4단자 / 두 독립 회로 모델 유지
- FUSE UI: 원본 source에서 실제형 2카트리지 디자인 반영
- expected_nets: 미작성
- operation_tests: 미작성
- 결선 채점: 차단
- 동작시험: 차단

## 다음 개발 원칙
다음 단계에서는 한 버전에 한 범위만 진행한다.
1. 사용자가 stable-fuse 실행 화면을 확인
2. Q-Net 010 terminal mapping + expected_nets만 개발
3. 그 버전의 결선 채점만 검증
4. 별도 다음 버전에서 operation을 개발
