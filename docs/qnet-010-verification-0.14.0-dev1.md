# Q-Net 공개문제 010 검증 기록 — 0.14.0 dev1

## 목적

0.13.0의 `draft` 차단을 유지하면서, 010번을 최초의 `verified` 공식문제로 만들기 전에 공통 기구와 데이터 표현의 선행 조건을 확인한다.

## 공식 근거

기준 원본은 `전기기능사-010-A4, 2025-08-04.pdf`이다.

- 6쪽: 제어판 내부 기구 배치
- 7쪽: 시퀀스 회로도
- 8쪽: 동작 사항
- 9쪽: 전자접촉기·EOCR·타이머·8P 릴레이 및 8P/12P 소켓 내부결선

## 이번 dev1에서 확정한 공통 12P 정의

### 전자접촉기 12P

- 주접점: 1-7, 2-8, 3-9 (NO)
- 보조 NO: 4-10 (`a1-a2`)
- 보조 NC: 5-11 (`b1-b2`)
- 코일: 6-12 (`A1-A2`)

기존 `magnetic_contactor_12p_training`의 전기적 정의와 공식 010 PDF 9쪽이 일치하므로 `definition_status`를 `verified`로 승격했다.

### EOCR 12P

- 주회로: 1-7 (`L1-U`), 2-8 (`L2-V`), 3-9 (`L3-W`)
- 트립 NC: 10-4 (`95-96`)
- 트립 NO: 11-5 (`97-98`)
- 전원: 6-12 (`A1-A2`)
- 8쪽 동작사항: 과부하 시 전동기 정지 및 YL 점등, RESET 후 초기 상태 복귀

기존 `eocr_12p_training`의 정의가 공식 010 PDF 8~9쪽과 일치하므로 `definition_status`를 `verified`로 승격했다.

## 새로 확인된 차단 사항: FUSE 표현

010 PDF의 시퀀스 회로도에는 제어전원 양쪽에 각각 퓨즈 심벌이 있어 **두 개의 독립된 퓨즈 경로**가 필요하다. 시험 유의사항도 퓨즈홀더 1차 측에 갈색과 회색 전선을 각각 사용한다고 명시한다.

그러나 0.13.0의 `problems/qnet_electrician_practical_010/board.json`에서 `F`는 현재 `F-1`, `F-2` 두 단자만 가진 단극 형태이다.

따라서 이 상태에서 010의 `expected_nets`를 작성하면 공식 회로의 두 퓨즈 경로를 정확하게 표현할 수 없을 가능성이 높다.

**결론: FUSE 모델/보드 표현을 먼저 2극 구조로 검증·확장하기 전에는 010을 `verified`로 올리지 않는다.**

## 현재 차단 유지 항목

- `problem.circuit.definition_status = structure_only`
- 구조화 회로 devices/terminals/contacts/coils 미작성
- `problem.operation = null`
- `answer.expected_nets = []`
- `answer.operation_tests = []`
- `manifest.status = draft`
- `answer.verification.status = unverified`

## 다음 작업 순서

1. 전체 0.13.0 소스 트리에서 현재 FUSE 기구 모델·렌더러·동작 엔진 참조 방식 확인
2. 기존 자체제작 문제 호환을 깨지 않는 2극 퓨즈 모델 또는 공식문제 전용 두 독립 퓨즈 인스턴스 표현 결정
3. 010 `circuit` 구조화
4. 010 기능 단자 기반 `expected_nets` 작성
5. 동일 기능 8P 접점 대체 규칙 검증
6. 공개 `operation` 및 비공개 `operation_tests` 작성
7. STOP/EOCR/타이머 우회 오답 주입 시험
8. 백엔드 API에서 `draft/unverified` 공식문제 직접 호출 차단 확인 및 필요 시 보강
9. 모든 자동·수동 시험 통과 후에만 010을 `verified`로 승격

## dev1 판정

- 8P 릴레이/타이머: 검증 유지
- 12P MC: 검증 완료
- 12P EOCR: 검증 완료
- FUSE 2극 표현: **차단**
- 010 expected_nets: **미작성 유지**
- 010 동작시험: **미작성 유지**
- 010 최종 상태: **draft 유지**
