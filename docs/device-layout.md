# 고정 기구 배치 작성 방법

전기기능사 실기 문제의 기구 위치는 문제지에 주어지는 공개 조건이다. 사용자가 위치를 맞히도록 채점하지 않고 `problem.json`의 `device_layout`에 명시한다.

```json
{
  "device_layout": {
    "schema_version": "1.0",
    "fixed_placements": [
      {
        "mount_device_id": "DEVICE-T1",
        "label": "T1 타이머",
        "device_type_id": "timer_8p",
        "graphic_type": "timer",
        "socket_id": "T1",
        "socket_type_id": "socket_8p_base"
      }
    ]
  }
}
```

## 필드

- `mount_device_id`: 문제 안에서 유일한 기구 ID
- `label`: 화면에 표시할 기구명
- `device_type_id`: `catalog/device_types.json`의 기구 유형
- `graphic_type`: `relay`, `timer`, `contactor` 중 하나
- `socket_id`: `board.json`에 있는 고정 소켓의 `item_id`
- `socket_type_id`: 보드 소켓과 동일한 8P 또는 12P 유형

장치명 문자열로 소켓을 추정하지 않는다. 모든 관계는 `mount_device_id`와 `socket_id`로 명시한다. 같은 기구나 소켓을 둘 이상 중복 배치할 수 없다.

## 공개 정보와 비공개 정답

`device_layout`은 문제지에 표시되는 배치이므로 공개 문제 상세과 `/operation-setup` API에 포함된다. 다음 정보는 `answer.json`에 두며 공개 API에 포함하지 않는다.

- 결선 정답
- 금지 연결
- 향후 동작 순서와 상태 판정
- 회로 내부 채점 데이터

기구 위치를 나타내던 기존 `mounting_answer`는 새 동작시험 입력으로 사용하지 않는다.

## 데이터가 없는 문제

`device_layout`을 생략하거나 `null`로 지정할 수 있다. 프로그램은 중단되지 않고 `이 문제의 기구 배치 정보가 준비되지 않았습니다.`라고 안내한다.

## 검증

```powershell
.venv\Scripts\python.exe -m tools.validate_problem problems\문제ID
.venv\Scripts\python.exe -m tools.validate_problem --all
```

검증기는 중복 기구·소켓, 없는 기구 유형, 보드에 없는 소켓, 8P·12P 유형 불일치를 확인한다.
