# 문제 데이터 폴더

문제마다 별도의 하위 폴더를 사용합니다. 세부 작성법은 `docs/problem-management.md`를 확인하세요.

예정 구조:

```text
problems/problem_001/
├─ manifest.json
├─ problem.json
├─ answer.json
├─ schematic.svg
└─ assets/
```

`answer.json`은 사용자 화면이나 일반 조회 API에 직접 노출하지 않습니다.

검증 명령:

```powershell
.venv\Scripts\python.exe -m tools.validate_problem --all
```
