# 문제·답안 관리 방법

## 기본 원칙

한 문제는 `problems` 아래의 독립 폴더 하나로 관리합니다. 화면에 공개되는 문제와 채점에 사용하는 답안은 파일을 분리합니다.

```text
problems/problem_001/
├─ manifest.json
├─ problem.json
├─ answer.json
├─ diagram.json
├─ schematic.svg
└─ assets/
```

- `manifest.json`: 문제 목록과 상태
- `problem.json`: 사용자에게 공개되는 설명과 회로 정보
- `answer.json`: 내부 채점용 정답
- `diagram.json`: 데이터 기반 SVG 회로도 배치
- `schematic.svg`: 회로도
- `assets`: 문제 전용 이미지

## Q-Net 공개문제 정책

- 시험 학습용 문제는 Q-Net 전기기능사 실기 공개문제 18문제로 고정합니다.
- Q-Net의 공식 변경이 없으면 문제를 추가·교체·변형하지 않습니다.
- 일반 사용자 화면에는 문제 추가·편집·새로고침 기능을 제공하지 않습니다.
- 공식 문제와 자체제작 기능검증 회로는 문제 선택 화면과 출처 데이터에서 분리합니다.
- 현재 저장소의 5개 문제는 모두 자체제작 또는 가상 검증 데이터이며 Q-Net 공개문제가 아닙니다.

## 자체제작 기능검증 회로 추가

1. `problems/_template` 폴더를 복사합니다.
2. 복사한 폴더명을 고유한 문제 ID로 변경합니다.
3. 세 JSON 파일의 `problem_id`를 폴더명과 동일하게 변경합니다.
4. `manifest.json`에 제목, 출처, 난이도와 예상 시간을 작성합니다.
5. `problem.json`에 공개 문제 설명과 지시사항을 작성합니다.
   장치·단자·접점·코일 작성 규칙은 `docs/circuit-data-model.md`를 확인합니다.
6. `schematic.svg`를 자체 제작 또는 사용 권한이 있는 회로도로 교체합니다.
   실제 상호작용 회로도는 `diagram.json`에 작성하며 세부 규칙은 `docs/schematic-diagram.md`를 확인합니다.
7. `answer.json`에 정답을 별도로 작성합니다.
8. 아래 검증 명령을 실행합니다.
9. 회로와 정답을 검토한 뒤 상태를 변경합니다.
10. 개발 환경에서 서버를 다시 시작하거나 내부 카탈로그 재적재 API로 확인합니다.

```powershell
.venv\Scripts\python.exe -m tools.validate_problem problems\problem_001
```

전체 문제 검사:

```powershell
.venv\Scripts\python.exe -m tools.validate_problem --all
```

오류가 있으면 종료 코드 1, 경고만 있으면 종료 코드 0을 반환합니다.

## ID와 상태

문제 ID는 영문 소문자, 숫자와 밑줄만 사용합니다.

```text
motor_control_001
practice_002
```

문제 상태:

- `draft`: 작성 중
- `reviewed`: 회로와 데이터 검토 완료
- `verified`: 정답과 동작까지 검증 완료

정답 상태:

- `unverified`: 미검증
- `reviewed`: 정답 검토
- `verified`: 실제 결선·동작까지 검증

`verified`는 실제 회로의 정상 동작과 정답을 확인한 후에만 사용합니다. 문제 상태가 `verified`인데 정답이 `verified`가 아니면 검증 오류가 발생합니다.

## 출처 표시

- `official`: 공개된 공식 자료를 사용 권한 범위에서 반영
- `reconstructed`: 수험자 기억 등에 기반한 복원
- `variant`: 기존 유형을 변형
- `practice`: 교육용 연습
- `original`: 자체 제작

공식 자료의 이미지나 도면을 포함하기 전에는 배포와 이용이 허용되는지 확인합니다. 자체 제작 또는 직접 다시 그린 도면도 원본 출처가 있다면 메모를 남깁니다.

## 문제와 답안을 분리하는 이유

분리하면 화면 API가 실수로 정답을 반환하는 일을 방지하고, 문제 설명과 정답을 독립적으로 검토할 수 있습니다. 웹 API에는 `answer.json`의 내용이 포함되지 않습니다.

다만 데스크톱 로컬 프로그램은 사용자의 PC에 문제 파일이 존재하므로 정답 파일을 암호학적으로 완전히 숨길 수 없습니다. 이 구조는 시험 보안용이 아니라 학습 프로그램에서의 우발적인 정답 노출 방지와 유지보수를 위한 것입니다.

## 채점 원칙

같은 전기적 연결이라도 물리적인 전선 순서가 다를 수 있습니다. 따라서 현재 채점에서는 다음을 함께 사용합니다.

- `required_connections`: 권장 물리 결선
- `expected_nets`: 전기적으로 같은 연결망
- `allowed_alternatives`: 검증된 대체 결선
- `operation_tests`: 실제 동작 결과

단순 전선 목록 비교만으로 최종 채점을 구현하지 않습니다.

## 기본 전선 색상

```text
L1      brown
L2      black
L3      gray
control yellow
```

현재 PE의 실제 전선 색상은 데이터 규칙으로 정의하지 않습니다. 회로도에서는 사용자의 요청에 따라 PE 선을 검은색으로 단순 표시할 수 있습니다. 정의된 전원선 색상 규칙이 다르면 문제 검증에 실패합니다.

## 공통 카탈로그

8P·12P 소켓의 실제 베이스 배열과 장치 유형은 `catalog` 폴더에서 공통 관리합니다. 개별 문제에 같은 배열을 복사하지 말고 `socket_type_id`와 `device_type_id`로 참조합니다. 실제 전기 자료를 확인하지 않은 장치 유형의 상태는 `unverified`로 유지하십시오.
