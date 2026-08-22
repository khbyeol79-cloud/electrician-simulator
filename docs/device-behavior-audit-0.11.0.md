# 0.11.0 공통 기구 동작 정의 감사

## 목적

이 문서는 `0.10.1`의 문제·자유회로 데이터에 흩어진 기구 동작 정의를 조사하여 `0.11.0` 공통 기구 동작 카탈로그의 경계를 정리한다. Q-Net 공식 회로 검증 문서가 아니라 현재 자체제작 기능 확인 데이터와 자동 테스트를 기준으로 한 개발 감사 결과다.

## 현재 정의 위치

| 정보 | 현재 위치 | 0.11.0 처리 |
|---|---|---|
| 기구 이름·분류·소켓·장착 | `catalog/device_types.json` | 기존 구조 유지 |
| 8P·12P 베이스 핀 배열 | `catalog/socket_types.json` | 기존 verified 정의 유지 |
| 기구 로컬 단자·코일·접점 | 각 `problems/*/problem.json`의 `circuit` | 공통 후보를 `device_behaviors.json`에 별도 추가 |
| 입력기구·타이머·표시등·모터 | 각 문제의 `operation` | 기구 고유 부분만 카탈로그로 분리 |
| 접촉기 역할·보호 대상·인터록 | 각 문제의 `operation` | 문제·작업공간 구성에 유지 |
| 사용자 실제 결선 | wiring draft와 승인 스냅샷 | 카탈로그에 포함하지 않음 |
| 채점 정답 | 비공개 `answer.json` | 카탈로그와 공개 API에서 제외 |

## 자유회로 시작 템플릿 비교

템플릿 A는 `operation_demo_001`, B는 `forward_reverse_interlock_demo_001`, C는 `eocr_sequence_demo_001`이다. 세 `board.json`의 SHA-256은 모두 `7e4ba3b1f4c1520add6b3a03de7da21efe5cfd8da201d03776e679463c6a9823`으로 실제 보드 배치는 동일하다.

| 항목 | 템플릿 A | 템플릿 B | 템플릿 C | 공통 모델 후보 | 차이 원인 | 검증 상태 |
|---|---|---|---|---|---|---|
| 기구 목록 | 12개 | 14개, MC2·PB2 추가 | 12개 | 기존 사용 기구 16개 모델 | 회로 목적 | reviewed 또는 unverified |
| 단자 목록 | 53개 | 65개 | 53개 | 로컬 terminal key | MC2와 외부 PB2 추가 | 기존 데이터 대조 |
| 코일 | VR1·MC1·T1 3개 | VR1·MC1·MC2·T1 4개 | VR1·MC1·T1 3개 | relay·timer·MC 모델 | 인스턴스 개수 | reviewed |
| NO/NC 접점 | NO 3개 | NO 4개·NC 2개 | NO 3개 | relay·timer·MC 접점 | 정역 인터록 보조접점 | 일부 unverified |
| 타이머 | T1 on-delay 1초 | 없음 | T1 on-delay 1초 | timer 8P partial | 문제 기능 | reviewed |
| MC 역할 | 모터 코일만 참조 | MC1 정회전·MC2 역회전 | MC1 정회전 | 모델에는 general만 | 문제별 역할 | 회로 구성에 유지 |
| 인터록 | 없음 | 전기적·기계적 각 1개 | 없음 | 공통 MC 모델에 상대 ID 없음 | 두 인스턴스 관계 | 회로 구성에 유지 |
| EOCR 보호 대상 | 없음 | MC1·MC2 코일과 M1 | MC1·T1 코일과 M1 | EOCR capability만 | 문제별 보호 범위 | 회로 구성에 유지 |
| 모터 상 연결 | M1 단방향 | M1 정·역회전 | M1 단방향 | U·V·W 단자 | 접촉기와 상순서 | 회로 구성에 유지 |
| internal connections | 7개 | 7개 | 7개 | MCCB·Fuse·EOCR 정상 경로 | 세 템플릿 동일 | 현재 엔진 기준 reviewed |

## 기구별 감사 결과

| 모델 | 현재 데이터 근거 | 카탈로그 범위 | 상태 | 제한사항 |
|---|---|---|---|---|
| terminal_block_position | TB 한 번호를 하나의 전기 노드로 사용 | 한 위치의 노드·용량 | reviewed | 20P 보드 조립은 후속 composer 담당 |
| mccb_3p_training | L1/T1, L2/T2, L3/T3와 정상 internal connection | 6단자·정상 경로 | reviewed | 실제 차단·트립 곡선 없음 |
| fuse_single_pole_training | F-1/F-2 정상 internal connection | 2단자·정상 경로 | reviewed | 용단 전류 계산 없음 |
| power_3p_control_training | 외부 PWR L/N/L1/L2/L3 | 단자만 정의 | reviewed | line·return·phase source는 작업공간 설정 |
| push_button_no/nc | PB0 NC, PB1·PB2 NO OperationControl | 수동 순간접점 | reviewed | 특정 START/STOP 역할 없음 |
| limit_switch_no | LS1 유지형 NO | 수동 유지접점 | reviewed | 회로별 초기 상태는 별도 설정 필요 |
| limit_switch_nc | 현재 사용 사례 없음 | 수동 유지 NC 접점 | unverified | 실제 문제 대조 필요 |
| auxiliary_relay_8p_training_partial | 코일 2-7, NO 6-3 | 현재 사용하는 핀만 | reviewed | 나머지 8P 접점은 미정의 |
| timer_8p_on_delay_training_partial | 코일 2-7, 계시 NO 1-3 | 현재 사용하는 핀·on-delay | reviewed | 나머지 핀과 다른 타이머 모드 미정의 |
| magnetic_contactor_12p_training | 코일 6-12, NO 4-10, NC 5-11 | 주접점·보조접점 후보 | unverified | 주접점 1-7·2-8·3-9 외부 근거 검증 필요 |
| eocr_12p_training | 12P 역할, L1-U·L2-V·L3-W, 95/96·97/98 역할 | 정상 주회로·트립 접점 후보 | unverified | 트립 접점의 실제 엔진 연결은 0.11.1 이후 |
| indicator_lamp_two_terminal | 외부 1·2 단자 | 단자·색상 설정 | reviewed | 실제 소비전력 계산 없음 |
| motor_three_phase | 외부 U·V·W | 3상 부하 단자 | reviewed | 방향은 모델이 아니라 실제 상순서로 결정 |
| socket_base_8p/12p | 기존 카탈로그와 핀 배열 테스트 | 베이스 핀 | verified | `wiring_base_front` 기준 |

## `internal_connections` 분류

세 자유회로 템플릿은 모두 다음 7개 연결을 사용한다.

| 연결 | 분류 | 카탈로그 포함 여부 | 이유 |
|---|---|---|---|
| MCCB-L1 ↔ MCCB-T1 | 기구 내부 정상 도통 | 포함 | 현재 교육 엔진에서 투입 상태를 고정 사용 |
| MCCB-L2 ↔ MCCB-T2 | 기구 내부 정상 도통 | 포함 | 동일 |
| MCCB-L3 ↔ MCCB-T3 | 기구 내부 정상 도통 | 포함 | 동일 |
| F-1 ↔ F-2 | 기구 내부 정상 도통 | 포함 | 현재 교육 엔진에서 정상 퓨즈를 고정 사용 |
| EOCR-L1 ↔ EOCR-U | 기구 내부 정상 주회로 경로 | 포함 | 현재 엔진의 교육용 EOCR 주회로 표현 |
| EOCR-L2 ↔ EOCR-V | 기구 내부 정상 주회로 경로 | 포함 | 동일 |
| EOCR-L3 ↔ EOCR-W | 기구 내부 정상 주회로 경로 | 포함 | 동일 |

현재 세 템플릿에는 문제 예제를 숨겨서 완성하는 사용자 결선용 `internal_connections`가 발견되지 않았다. 다만 MCCB 차단 상태와 퓨즈 용단 상태는 아직 동적으로 열리지 않으므로 실제 물리 장치의 완전한 모델이 아니라 정상 상태 교육용 경로다.

코일 상태로 변하는 릴레이·타이머·MC 접점은 `intrinsic_connections`로 분류하지 않았다. 해당 접점은 `contacts`와 actuation으로 유지한다.

## 인스턴스와 회로 구성의 경계

카탈로그 인스턴스 생성기는 다음 fragment를 만들 수 있다.

- CircuitDevice
- CircuitTerminal
- CircuitCoil
- 코일 또는 타이머로 움직이는 CircuitContact
- PB·LS OperationControl
- OperationTimer
- OperationIndicator
- 역할이 `general`인 OperationContactor
- 기구 고유 intrinsic connection
- local key에서 실제 ID로의 매핑

다음 항목은 완전한 회로 composer가 필요한 지연 항목이다.

- 작업공간의 OperationPower
- 모터와 정·역 접촉기 관계
- EOCR 보호 대상 코일과 모터
- EOCR 보호 접점의 런타임 상태 연결
- 전기적·기계적 인터록 인스턴스 관계
- 외부선과 TB 번호 배정

따라서 단일 기구 fragment를 억지로 완전한 `OperationDefinition`으로 만들지 않는다.

## 기존 자유회로 호환성

`0.11.0`은 기존 템플릿 ID와 저장된 circuit·operation JSON을 변경하지 않는다. 기존 작업공간은 종전 문제 패키지의 정의로 실행되고, 새 카탈로그와 인스턴스 생성기는 후속 통합 보드 구현을 위한 독립 기반으로만 추가된다.

## 후속 작업

### 0.11.1

- MC 주접점과 실제 사용자 결선을 이용한 3상 경로 계산 강화
- EOCR 95-96·97-98 접점과 보호 상태 연결
- MCCB·Fuse 상태를 동적 장치로 확장할 필요성 검토
- 숨은 역할 기반 차단보다 실제 NC 인터록 결선을 우선하는 판정 정리

### 0.11.2

- 공통 모델의 superset으로 통합 기본보드 구성
- 기존 3개 템플릿은 저장 작업공간 호환용으로 유지
- 템플릿별로 하드코딩된 역할을 작업공간 구성 데이터로 이동

### 0.12.0

- TB5·TB6만 있는 빈보드
- 기구 팔레트·설치·삭제·이동
- 인스턴스 fragment를 조합하는 완전한 circuit/operation composer

## 안전 범위

이 카탈로그는 교육용 논리 도통 모델이다. 실제 전압강하, 전류, 차단전류, 접촉저항, 발열, 모터 RPM·토크와 절연 안전을 계산하지 않으며 실제 전기작업의 안전 판정 자료로 사용할 수 없다.
