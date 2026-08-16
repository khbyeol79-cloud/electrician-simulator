# 결선 문제 추가 방법

1. 문제 폴더에 `board.json`을 만들고 manifest의 `files.board`에 등록합니다.
2. 모든 핀에 문제 내에서 유일한 `terminal_id`를 부여합니다.
3. 소켓 핀 순서와 `socket_type_id`가 카탈로그 규격과 일치하는지 확인합니다.
4. 비공개 `answer.json`의 `wiring_connections`에 필수 연결을 작성합니다.
5. 금지 연결은 `wiring_forbidden_connections`에 작성합니다.
6. `python -m tools.validate_problem --all`로 검증합니다.

물리 전선 색상은 L1 갈색, L2 검은색, L3 회색, 제어선 노란색을 사용합니다. PE 실제 전선 색상은 현재 정답 규칙으로 확정하지 않습니다. 요약 모드의 연결 구분 색상은 물리 전선 색상과 별도이며 양쪽 단자에 같은 색과 상대 단자명을 표시합니다.
