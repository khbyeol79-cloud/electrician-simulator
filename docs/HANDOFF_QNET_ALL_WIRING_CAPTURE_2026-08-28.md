# Q-Net 001~018 결선 저장 모드 인계 — 0.14.0-dev12

## 구조

- `backend/app/domain/wiring_capture.py`: 저장 허용 연결, 구조 경고, workspace/snapshot/export/import 모델.
- `backend/app/services/wiring_capture_service.py`: 정답 독립 구조 검사.
- `backend/app/repositories/practice_wiring_repository.py`: 현재 draft, 목록, 스냅샷, 복제 저장.
- `backend/app/api/wiring.py`: workspace/draft/snapshot/export/import API.
- `frontend/src/pages/WiringPage.tsx`: 작업공간 UI, 직렬 debounce 자동저장, 버전 및 JSON UI.
- `frontend/src/pages/OperationTestPage.tsx`: 선택 workspace를 기존 practice engine으로 전달.

## DB

Schema 12는 `practice_wiring_drafts`에 `workspace_name`, `warnings_json`, `created_at`, `latest_snapshot_id`를 추가하고 `practice_wiring_snapshots`를 생성한다. ALTER와 backfill은 반복 실행 가능하다. 사용자 식별은 기존 `UserDatabasePool`의 사용자별 DB를 그대로 사용한다.

## API

- `GET/POST /api/problems/{problem_id}/practice-workspaces`
- `GET/PUT/DELETE /api/problems/{problem_id}/practice-drafts/{workspace_id}`
- `GET/POST .../snapshots`
- `POST .../snapshots/{snapshot_id}/clone`
- `GET .../export`
- `POST /api/problems/{problem_id}/practice-imports`
- `GET .../operation-setup?workspace_id=...`

데스크톱 `JSON 내보내기`는 pywebview의 `ALLOW_DOWNLOADS`가 반드시 활성화되어야 한다. 프런트는 현재 편집 내용을 먼저 저장하고 export API의 JSON Blob을 다운로드하며, WebView2는 기본 다운로드 폴더를 시작 위치로 하는 저장 대화상자를 연다.

`practice-capture-workspace`는 안내 배너, 작업공간 도구줄, 결선 제목, 결선판을 각각 독립 Grid 행으로 둔다. 일반 결선용 2행 Grid로 되돌리면 내보내기 버튼이 접근성 트리에는 남지만 화면에서 잘리므로 이 클래스와 회귀 테스트를 유지한다.

ID는 서버에서 생성한다. URL의 problem/workspace와 현재 사용자 DB가 소유권 경계다. import의 원본 ID는 신뢰하지 않고 새 작업공간과 스냅샷을 만든다.

## 저장과 검사

프런트는 650ms debounce와 직렬 Promise queue를 사용한다. 최신 sequence만 상태를 갱신하므로 오래된 응답이 UI를 되돌리지 않는다. 작업공간 전환 전에 현재 변경을 즉시 저장한다.

Capture 모델은 자기 연결도 표현할 수 있다. 구조 검사는 존재/범위/활성 단자, 자기 연결, 중복, 수용량, 공개 회로로 명확한 단락·우회만 경고한다. 답안, expected net, 점수는 참조하지 않는다. 기존 엔진에 넘길 때만 strict `WiringConnection`으로 변환하며 변환 불가 draft는 실행하지 않는다.

## 엔진 상태

- Q008·010·018: 기존 명시적 functional practice engine 사용.
- 나머지 Q-Net: 결선 저장만 가능하고 검증 대기 안내.
- 새로운 기구·접점·코일·동작 시나리오는 추정하지 않았다.

## 제어함 기구 배치

Q-Net 001~018의 `board.json`은 모두 `layout_mode: fixed`이다. 공개 PDF 6쪽을 근거로 작성된 x/y 좌표를 API가 그대로 반환하며, 공통 `auto_rows` 정렬을 적용하지 않는다. 새로운 문제 보드를 작성할 때도 PDF 고정 배치라면 반드시 `fixed`를 명시하고 원본 좌표/API 좌표 회귀 테스트를 유지한다.

## FUSE 모델

지원하는 FUSE는 `fuse_dual_4terminal_training` 하나뿐이다. 한 몸체 안에서 F-1↔F-2와 F-3↔F-4가 서로 독립된 회로로 동작한다. 1회로 2단자 모델과 팔레트 생성 항목은 제거했다. 저장된 편집 가능 자유회로에 구형 식별자가 있으면 조회/저장 과정에서 4단자 모델로 변환하되 기구 인스턴스 ID와 기존 결선을 보존한다. SQLite 레코드나 작업공간을 삭제하지 않는다.

## 정보 보호

Export는 schema/problem/workspace/snapshot/시간/connections/structural warnings만 반환한다. answer repository, private audit, operation test, 로컬 경로는 사용하지 않는다. 배포 ZIP에서 `docs/private`와 비공개 테스트·fixture를 제외해야 한다.

## 실행과 테스트

```powershell
Set-Location "D:\project\elec\electrician-simulator-dev"
$env:ELECTRICIAN_DATA_DIR="D:\project\elec\qnet-18\handoff-smoke"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\test_all.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_web.ps1
```

## 후속 권장 순서

1. 실제 사용자 결선 파일을 import해 008·010·018 엔진 표본을 늘린다.
2. 작업공간 이름 변경 UI와 선택적 스냅샷 메모 입력 UI를 추가한다.
3. 공식 근거가 확보된 문제만 별도 엔진 검증 작업으로 승격한다.
4. 기존 deprecation warning은 의존성 호환 계획과 함께 처리한다.

## 미해결

- 엔진 미검증 15개 문제는 의도적으로 결선 저장 전용이다.
- 브라우저에서 강제 저장 실패 및 파일 chooser round-trip은 미실행이다.
- 제품 표시 버전은 정식 배포 전까지 0.13.0을 유지한다.
