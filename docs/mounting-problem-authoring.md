# 기구 장착 문제 작성 방법

기구 장착은 공개 문제 데이터와 비공개 정답 데이터를 분리한다. 사용자가 선택할 수 있는 기구와 장착 가능한 소켓은 `problem.json`에, 정확한 기구·소켓 대응은 `answer.json`에 작성한다.

## 공개 데이터

`problem.json`에 다음 구조를 추가한다.

```json
{
  "mounting": {
    "schema_version": "1.0",
    "available_devices": [
      {
        "mount_device_id": "DEVICE-T1",
        "label": "T1 타이머",
        "device_type_id": "timer_8p",
        "graphic_type": "timer",
        "compatible_socket_type_ids": ["socket_8p_base"]
      }
    ],
    "mount_targets": [
      {
        "socket_id": "T1",
        "socket_type_id": "socket_8p_base",
        "enabled": true,
        "allowed_device_type_ids": ["timer_8p"]
      }
    ]
  }
}
```

- `mount_device_id`는 문제 안에서 유일해야 한다.
- `device_type_id`는 `catalog/device_types.json`에 등록된 유형을 사용한다.
- `graphic_type`은 `relay`, `timer`, `contactor` 중 하나다.
- `socket_id`는 같은 문제의 `board.json`에 있는 8P 또는 12P 소켓 `item_id`와 일치해야 한다.
- `socket_type_id`는 보드 소켓과 같아야 한다.
- `allowed_device_type_ids`로 같은 8P 소켓이라도 릴레이용과 타이머용 위치를 구분한다.
- 장착 기능을 제공하지 않는 문제는 `mounting`을 생략하거나 `null`로 지정할 수 있다.

## 비공개 정답

`answer.json`에 다음 구조를 작성한다.

```json
{
  "mounting_answer": [
    {
      "mount_device_id": "DEVICE-T1",
      "socket_id": "T1"
    }
  ]
}
```

정답에 사용하는 기구와 소켓은 모두 공개 `mounting` 데이터에 존재해야 하며 서로 호환되어야 한다. 한 기구나 한 소켓을 두 번 사용할 수 없다. 이 배열은 공개 문제 상세와 `/mounting` API에 포함되지 않는다.

## 검증

```powershell
.venv\Scripts\python.exe -m tools.validate_problem problems\문제ID
.venv\Scripts\python.exe -m tools.validate_problem --all
```

검증기는 중복 ID, 없는 기구 유형, 없는 소켓, 보드와 다른 소켓 형식, 호환되지 않는 정답을 검사한다. 정답 검증 상태가 `unverified`이면 제출 기록은 남지만 정오 채점은 하지 않는다.
