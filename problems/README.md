# 문제 데이터 폴더

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
`problem.json`의 `mounting`은 사용자에게 공개되는 기구와 장착 가능한 소켓을 정의합니다.
`answer.json`의 `mounting_answer`는 비공개 정답이며 일반 조회 API에 포함되지 않습니다.

기구 장착 문제 작성법은 `docs/mounting-problem-authoring.md`를 확인하세요.

검증 명령:

```powershell
.venv\Scripts\python.exe -m tools.validate_problem --all
```
