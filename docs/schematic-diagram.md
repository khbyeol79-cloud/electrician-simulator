# 구조화 SVG 회로도 작성법

문제의 `diagram.json`은 회로도 화면 배치만 담당합니다. 전기 연결과 정답은 각각 `problem.json`의 `circuit`와 비공개 `answer.json`을 사용합니다.

## 파일 관계

```text
manifest.json → diagram.json
problem.json  → 장치·단자·접점·코일·질문
answer.json   → 소켓번호 정답(비공개)
```

`view_box`는 브라우저 픽셀이 아닌 SVG 내부 좌표입니다. `sections`로 주회로와 제어회로를 구분하고, `elements`는 React의 타입별 SVG 기호로 렌더링됩니다. 임의 SVG 문자열은 삽입하지 않습니다.

선택 가능한 요소에는 `interactive: true`, `question_id`, `circuit_ref_type`, `circuit_ref_id`가 모두 필요합니다. 질문 대상 ID와 diagram의 참조 ID가 다르면 문제는 자동 제외됩니다.

`conductors`의 각 선분은 수평 또는 수직이어야 합니다. 전원 표시색은 L1 갈색, L2 검정, L3 회색입니다. 현재 PE는 색상을 정의하거나 회로도에 별도 표시하지 않습니다. 이 선은 문제에 인쇄된 회로도 표현이며 후속 배선판에서 사용자가 연결할 전선과 별개입니다.

## 가상 문제

`training_socket_demo_001`은 접점 선택과 채점 기능 확인 전용입니다. VR1과 핀 번호는 실제 기기를 설명하지 않으며 실제 전기기능사 답안으로 사용할 수 없습니다.
