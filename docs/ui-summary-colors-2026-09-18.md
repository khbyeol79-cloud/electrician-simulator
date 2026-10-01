# 제어함 요약모드 기구 색상 보강

- 공개문제 001~018 보드의 15종 기구 ID 전수 확인.
- 미지정 X, FR, T, FLS에 녹색(#16a34a), 올리브색(#6b7c0f), 파란색(#2563eb), 하늘색(#06b6d4) 지정.
- 나머지 EOCR, F, MC1, MC2, MCCB, T1, T2, TB5, TB6, X1, X2는 기존 색 유지.
- 같은 기구는 모든 문제에서 같은 색 사용. X/X1 및 T/T2는 같은 문제에서 함께 사용되지 않아 색을 공유한다.
- 18개 보드마다 미지정 기본 회색 및 문제 내 색상 중복이 없음을 자동 검사.
- 기구 이름표와 해당 기구를 가리키는 단자 요약 표시가 같은 색을 참조함.
- 사용자 결선, 물리 전선 색상(PE 녹색 포함), 회로 엔진 및 문제 데이터 변경 없음.

## 검증

- 관련 SummaryReadability 4개 통과.
- 프런트엔드 전체 107개 통과.
- TypeScript 검사 및 production build 통과.
- Python 전체: `.venv/Scripts/python.exe -m pytest -o addopts='' -q --basetemp <data/dev/pytest-summary-colors-GUID>` — 452개 통과(210.80초), 기존 Starlette 경고 1개.
- 문제 패키지 검사: 23개, 오류 0, 기존 경고 19.
- git diff --check 통과.
