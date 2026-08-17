# 문제 데이터 폴더

0.8.0에는 자체 제작 기능 검증 문제 `forward_reverse_interlock_demo_001`과 `eocr_sequence_demo_001`이 포함됩니다. 두 문제는 Q-net 공개문제 원본이 아닙니다.

정·역회전 문제는 공개 `problem.json.operation`에 contactors, interlocks, protection_devices를 정의하고, 비공개 `answer.json.operation_tests`에 자동시험 순서와 기대 상태를 저장합니다. 공개 API에는 `operation_tests`를 포함하지 않습니다.

문제마다 별도의 하위 폴더를 사용합니다. 세부 작성법은 `docs/problem-management.md`를 확인하세요.

예정 구조:

```text
problems/problem_001/
├─ manifest.json
├─ problem.json
├─ answer.json
├─ diagram.json
├─ schematic.svg
└─ assets/
```

`answer.json`은 사용자 화면이나 일반 조회 API에 직접 노출하지 않습니다.
`diagram.json`은 접점 선택용 구조화 SVG 배치 데이터입니다.
장치와 소켓 유형은 `catalog` 폴더의 공통 정의를 ID로 참조합니다.
`problem.json`의 `device_layout.fixed_placements`는 문제지에 제시되는 고정 기구 위치이며 공개 데이터입니다.
결선 정답과 향후 동작시험 판정 데이터는 `answer.json`에 작성하고 일반 조회 API에 포함하지 않습니다.

고정 기구 배치 작성법은 `docs/device-layout.md`, 동작시험 작성법은 `docs/operation-simulation.md`를 확인하세요. 기존 `mounting`과 `mounting_answer`는 0.6.0 데이터 호환을 위해 읽을 수 있지만 새 문제에서는 사용하지 않습니다.

검증 명령:

```powershell
.venv\Scripts\python.exe -m tools.validate_problem --all
```
