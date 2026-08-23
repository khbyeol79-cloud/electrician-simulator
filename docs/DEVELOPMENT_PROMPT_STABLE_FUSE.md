# 안정화 + FUSE 디자인 개발 기준

## 목적
마지막으로 정상 실행이 확인된 전체 프로젝트 소스를 기준으로 안정성을 우선한다. 이번 빌드에서는 Q-Net 010의 채점·동작시험 개발을 진행하지 않고, 이미 검증된 4단자 FUSE 모델을 실제 원본 UI에서 정확하게 표현하는 데 집중한다.

## 절대 변경하지 않을 영역
- Q-Net 010 `expected_nets`
- Q-Net 010 `operation_tests`
- Q-Net 010 `manifest.status`
- Q-Net 010 `answer.verification.status`
- simulation engine
- operation API 동작 규칙
- wiring grading 서비스 동작 규칙
- 기존 자체제작 문제의 채점/동작 방식

## 허용된 변경
1. `frontend/src`의 FUSE 전용 렌더러
2. FUSE 전용 CSS
3. FUSE UI 회귀 테스트
4. 이미 추가된 4단자 FUSE 때문에 오래된 인덱스/개수 가정을 하던 테스트의 유지보수
5. 실행용 `frontend/dist`를 원본 FUSE 렌더러와 일치시키는 작업
6. 검증 문서와 미리보기

## FUSE 확정 구조
- 기구: `F` 1개
- 외부 단자: 1, 2, 3, 4
- 내부 독립 회로: `1 ↔ 2`, `3 ↔ 4`
- 교차 회로는 절연
- 소켓 삽입형이 아니므로 `pin_number = null`, `compatible_socket_type_ids = []`
- Q-Net 010 화면 배치: 상단 1/3, 하단 2/4

## UI 요구
- 한 몸체 안에 좌우 두 개의 퓨즈 카트리지
- 네 결선점은 기존 board.json endpoint 좌표를 그대로 사용
- 공통 component 렌더러가 아닌 4단자 FUSE에만 전용 외형 적용
- 기존 2단자 FUSE는 기존 외형/데이터 호환 유지

## 안정화 완료 조건
- 백엔드 전체 테스트 통과
- CatalogService 정상 초기화
- Q-Net 18개 로딩
- Q-Net 010은 계속 `draft / unverified`
- FUSE 4단자/두 독립회로 검사 통과
- TypeScript/TSX 구문 검사 통과
- 실행용 JS bundle 구문 검사 통과
- 실행용 bundle/CSS에 새 FUSE renderer가 존재
- FastAPI가 실제 `frontend/dist`와 Q-Net 18문제를 정상 제공
- 전체 프로젝트를 새 폴더에 풀어 동일 검사를 다시 통과

## 결과물
부분 패치가 아니라 `electrician-simulator-0.13.0-stable-fuse-full.zip` 전체 프로젝트 하나를 제공한다.
