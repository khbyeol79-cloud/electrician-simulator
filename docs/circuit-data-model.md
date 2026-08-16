# 회로 데이터 모델과 참조 규칙

## 데이터 계층

- `catalog/socket_types.json`: 실제 소켓 베이스의 물리 핀 위치
- `catalog/device_types.json`: 재사용 가능한 장치 유형과 호환 소켓
- `problem.json`: 문제에 배치된 장치·단자·접점·코일·소켓번호 질문
- `answer.json`: 소켓번호 정답, 필수 결선, 예상 네트워크와 금지 결선

화면 좌표는 `board_position`에 0~1 정규화 값으로 저장합니다. 전기 연결은 좌표가 아니라 `X1-1`, `MC1-A1`, `TB5-01`, `L1`, `PE` 같은 고유 `terminal_id`로만 계산합니다.

## 소켓 베이스 기준

배선 작업자가 장치를 꽂기 전의 베이스를 정면에서 본 방향입니다.

| 규격 | 상단 왼쪽→오른쪽 | 하단 왼쪽→오른쪽 |
|---|---|---|
| 8P | 6, 5, 4, 3 | 7, 8, 1, 2 |
| 12P | 1, 2, 3, 4, 5, 6 | 7, 8, 9, 10, 11, 12 |

릴레이·타이머의 내부 접점 회로와 소켓 베이스 핀 위치는 별개의 데이터입니다. 실제 내부 접점 번호가 확인되지 않은 장치에는 `electrical_definition_status: unverified`를 유지합니다.

## 문제 회로

`circuit.schema_version`은 현재 `1.0`입니다. `definition_status`는 다음 중 하나입니다.

- `structure_only`: 구조와 참조 검사만 가능한 데이터
- `functional`: 검증된 전기 동작 계산까지 가능한 데이터

장치에는 `device_type_id`와 필요 시 `socket_type_id`를 지정합니다. 소켓 핀 단자는 `terminal_type: socket_pin`과 `pin_number`가 필요합니다. 접점과 코일은 존재하는 장치·단자·코일 ID만 참조할 수 있습니다.

## 소켓번호 질문과 정답

질문의 위치와 라벨은 `problem.json`의 `socket_questions`에 둡니다. 실제 핀 정답은 `answer.json`의 `socket_pin_answers`에만 둡니다.

```json
{
  "socket_pin_answers": {
    "SQ001": { "upper": 1, "lower": 4 }
  }
}
```

답안의 질문 ID, 슬롯 ID와 핀 번호는 문제의 질문 및 대상 장치 소켓과 모두 일치해야 합니다.

## 자동 제외 조건

중복 ID, 존재하지 않는 카탈로그 항목, 잘못된 소켓 핀, 끊어진 접점·코일 참조, 잘못된 NO/NC 기본 상태, 존재하지 않는 정답 단자 등이 발견되면 문제는 선택 목록에서 제외됩니다. 검증 오류에는 문제 ID, 파일, 필드 경로와 오류 코드가 기록됩니다.
