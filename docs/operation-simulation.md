# 동작시험 데이터 작성법

0.7.0의 동작시험은 공개 `problem.json.operation`, 공개 `problem.json.circuit`, 사용자가 정상 제출한 결선 스냅샷을 이용합니다. 자동 검사의 절차와 기대 상태는 비공개 `answer.json.operation_tests`에 저장합니다.

## 공개 데이터

`operation.simulation_status`가 `functional`인 문제만 전원을 투입할 수 있습니다. `preview` 또는 필드가 없는 기존 문제는 읽기 전용 미리보기만 제공합니다.

```json
{
  "operation": {
    "schema_version": "1.0",
    "simulation_status": "functional",
    "power": {
      "line_terminal_id": "TB5-04",
      "return_terminal_id": "TB6-01",
      "phase_terminal_ids": ["TB5-01", "TB5-02", "TB5-03"]
    },
    "controls": [],
    "timers": [],
    "indicators": [],
    "motors": [],
    "internal_connections": []
  }
}
```

- `controls`: PB, LS, 선택스위치의 ID, 순간·유지 방식, NO·NC, 양단을 정의합니다.
- `timers`: 코일 ID, `on_delay`, 지연시간(ms), 시간 접점 ID를 정의합니다.
- `indicators`: 램프 양단과 표시색을 정의합니다. 녹색은 표시등 색상에만 사용하며 PE 색상으로 사용하지 않습니다.
- `motors`: 정·역 코일, 모터 3상 단자, 전원 상 단자와 정상 상순서를 정의합니다.
- `internal_connections`: MCCB·퓨즈 등 문제지에 공개된 장치 내부의 고정 도통 관계를 정의합니다.

모든 단자·코일·접점 참조는 `circuit`에 존재해야 합니다. 문제 검증기는 누락된 참조를 오류로 처리합니다.

## 비공개 자동 검사

```json
{
  "operation_tests": [
    {
      "test_id": "SELF_HOLD_START_STOP",
      "label": "자기유지 기동·정지",
      "steps": [
        {"action": "set_power", "value": true},
        {"action": "press_control", "control_id": "PB1"},
        {"action": "release_control", "control_id": "PB1", "expect": {"coils": {"MC1-COIL": true}}}
      ]
    }
  ]
}
```

지원 동작은 `set_power`, `press_control`, `release_control`, `toggle_control`, `advance_time`입니다. `expect`에는 `powered`, `coils`, `contacts`, `timers`, `indicators`, `motors`의 필요한 값만 작성합니다. API는 시험 단계와 기대 상태를 반환하지 않고 시험명·통과 여부·안내만 반환합니다.

## 정상 제출 스냅샷

동작시험은 `wiring_drafts`를 사용하지 않습니다. `wiring_attempts`에서 `gradable=1`, `overall_correct=1`, 현재 문제 버전과 일치하는 가장 최근 제출을 사용합니다. 이후 임시 배선을 수정해도 기존 동작시험 입력은 바뀌지 않으며 새 정상 제출이 생길 때만 갱신됩니다.

## 지원 범위와 제한

엔진은 도통 그래프, NO·NC·전환 접점, 코일, 자기유지, ON delay 타이머, 램프, 논리적 3상 모터 상태를 계산합니다. 실제 전류·전압강하·발열·절연·기계 부하·안전 적합성을 계산하지 않습니다.
