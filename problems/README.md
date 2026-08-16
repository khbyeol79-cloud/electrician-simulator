# 문제 데이터 폴더

문제마다 별도의 하위 폴더를 사용합니다. 세부 JSON 스키마와 검증 도구는 2단계에서 구현합니다.

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

