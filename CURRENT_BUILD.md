# Current Recommended Build

**빌드명:** 0.13.0 stable-fuse

이 빌드는 Q-Net 010을 새로 개방하는 개발본이 아니라, 마지막 정상 실행 전체 소스를 기준으로 FUSE 모델/화면만 안정화한 보수적 빌드입니다.

## 이번 빌드에서 바뀐 것
- Q-Net 010의 `F`를 4단자 2회로 퓨즈홀더로 표시하는 원본 프런트엔드 renderer 추가
- 두 퓨즈 카트리지의 실제형 화면 표현
- 기존 4단자 FUSE 카탈로그/보드 모델에 맞도록 오래된 테스트 정리
- 실행용 frontend dist를 원본 FUSE renderer와 동기화

## 이번 빌드에서 의도적으로 바꾸지 않은 것
- Q-Net 010 expected_nets
- Q-Net 010 operation_tests
- simulation engine
- grading engine
- 공식문제 API 개방 조건

따라서 Q-Net 010은 여전히 `draft / unverified`이며 결선 채점과 동작시험은 차단된 상태가 정상입니다.
