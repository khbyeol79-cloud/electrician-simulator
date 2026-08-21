# 전기기능사 시퀀스 결선 시뮬레이터

Windows 데스크톱 프로그램과 웹 브라우저에서 동일한 React 화면을 사용하는 전기기능사 실기 학습 프로그램입니다. 현재 버전은 0.9.4이며 TB 번호 자유 선택, 전기적 연결관계 채점, 데이터 기반 회로도 분석과 논리 동작시험을 포함합니다.

시험 학습 콘텐츠는 Q-Net 전기기능사 실기 공개문제 18문제로 고정합니다. Q-Net이 공식 공개문제를 변경하지 않는 한 일반 사용자가 문제를 추가·편집하는 기능은 제공하지 않습니다. 현재 저장소에는 검증용 자체제작 회로 5개만 있고 검증된 Q-Net 18문제 데이터는 아직 들어 있지 않습니다. 프로그램은 이를 문제 선택 화면에서 서로 다른 영역으로 표시하며 자체제작 회로를 공식 문제로 취급하지 않습니다.

회로도 분석 → 제어함 결선 → 동작시험의 3단계로 진행합니다. 0.8.0에서는 가장 최근의 정상 결선 제출 스냅샷을 이용해 전원, PB·LS, 릴레이, ON delay 타이머, MC1·MC2 자기유지와 인터록, EOCR 트립, 표시등과 3상 모터 방향을 계산합니다. 기구 위치는 문제지의 공개 조건이며 동작시험 화면에 자동으로 삽입됩니다.

## 현재 구현된 기능

- React + TypeScript 공통 화면
- 회로도 분석·제어함 결선·동작시험 3단계 이동
- FastAPI 상태 API와 React SPA 제공
- SQLite 스키마 자동 초기화
- 데스크톱 실행 시 빈 포트 자동 선택
- pywebview 종료 시 로컬 FastAPI 서버 종료
- 웹/LAN 확장이 가능한 실행 설정
- 회전 로그와 한국어 오류 화면
- Python 및 프런트엔드 자동 테스트
- 문제·답안 JSON 분리와 JSON Schema 검증
- 손상된 문제와 중복 ID 자동 제외
- 문제 목록·공개 상세·새로고침 API
- 문제 선택 창, 상태 배지와 마지막 선택 복원
- 내부 전용 답안 저장소와 일반 API 정답 노출 방지
- 복사용 문제 템플릿과 구조 확인용 샘플 문제
- 장치·단자·접점·코일의 엄격한 데이터 모델
- 8P·12P 소켓 베이스 공통 카탈로그
- 문제와 정답의 단자 참조 무결성 검사
- 회로 데이터 요약 및 소켓 핀 배열 진단 화면
- 구조화된 `diagram.json` 기반 SVG 회로도
- 주회로·제어회로 구역과 전원선 색상 표시
- 접점 키보드·마우스 선택과 주변 번호 마커
- 확대·축소·화면 맞춤·100%·드래그 이동
- 8P·12P 소켓번호 입력과 임시 답안 복원
- 검증 상태를 확인하는 서버 채점과 SQLite 제출 기록
- 실제 제어함 그래픽·요약 결선, 자동 직교 경로와 전선 색상 변경
- 요약 모드에서 상대 단자를 기구명 없이 `L1`, `1`, `4` 같은 슬롯명으로만 표시
- 선택 전선의 원색 위에 청록색 고대비 외곽 강조선을 표시하고 선택 변경·삭제와 연동
- PB·LS·표시등·모터·전원 등 문제별 외부 기구선의 TB 배정
- 창 폭과 최대화 상태가 바뀌어도 보드와 겹치지 않는 외부 기구선 고정 영역
- TB5·TB6 명칭을 슬롯 번호와 겹치지 않게 상·하단으로 분리 표시
- 외부선 클릭·키보드 선택·드래그 후 원하는 TB5·TB6 단자에 연결
- `functional`·`free_junction`·`external` 단자 역할과 기능 단자 네트워크 서명
- 정답 예시와 다른 TB 번호·점퍼 길이를 허용하는 전기적 동등성 채점
- 누락 네트워크·잘못 합쳐진 회로·불필요한 기능 연결·고립 TB 점퍼·루프 구분
- 한 단자에 연결된 여러 전선의 좌우 분리 표시와 요약 모드 `+N` 연결 목록
- 일반 기구 단자는 한 번호당 최대 두 가닥까지만 연결
- TB5·TB6은 세로 방향의 같은 슬롯을 외부측 2가닥과 내부측 2가닥으로 나누어 총 4가닥까지 연결
- TB의 한쪽 면에서 세 갈래 이상 분기할 때는 인접 TB 슬롯과 점퍼를 사용해 면별 두 가닥 이하로 분산
- 문제의 `row`와 좌우 순서에 따라 장치를 TB5·TB6 경계 안에 균등 배치하는 자동 정렬
- EOCR·전자접촉기 12P 소켓과 타이머·릴레이 8P 소켓의 실제 단자 배열 및 역할 표시
- 회로도 분석 결과를 결선 화면에서 확인하는 확대·이동 참고창
- 결선 제출 성공 후 동작시험 화면 자동 이동
- 문제지 공개 조건인 8P·12P 릴레이·타이머 고정 배치
- 사용자 정상 제출 결선과 고정 기구를 함께 표시하는 읽기 전용 동작시험 화면
- 동작시험에서 내부선과 외부 기구선을 분리 렌더링하여 외부 단자 좌표가 없는 승인 결선도 안전하게 표시
- 정상 결선 제출 스냅샷과 편집 중 임시 배선 분리
- 전원 ON/OFF와 오류 차단
- 순간동작 PB와 유지형 LS의 마우스·키보드 조작
- 릴레이 NO·NC·전환 접점과 자기유지 상태 계산
- ON delay 타이머의 결정적 시간 진행과 완료 전 초기화
- 표시등 도통 상태와 3상 모터 정·역회전·결상·동시 여자 판정
- 직접 단락·상간 단락·불안정 회로 오류 표시
- 비공개 동작시험 조건을 이용한 격리 자동 동작검사
- 결선 구조가 틀렸지만 비공개 동작 요구조건은 통과한 경우 `동작하지만 오답`으로 별도 분류
- 동작시험 결과 SQLite 기록과 0.6.0·0.6.1·0.7.0 DB 자동 호환
- MC1·MC2 정·역회전, 전기적·기계적 인터록과 정지 후 방향 전환
- EOCR 교육용 과부하 주입, 수동 복귀와 복귀 후 재시작
- 3상 결상·상순서·동시 투입 위험 판정과 동작 이벤트 기록
- 문제 참조 무결성을 한 번에 검사하는 `scripts/validate_problems.py`
- 자체 제작 기능 확인 문제 `operation_demo_001`
- LAN 브라우저별 SQLite 파일과 동작시험 세션 분리(`X-User-Id` 내부 식별자)
- 자유회로 작업공간 저장 및 정답 없이 공통 논리 엔진을 시작하는 백엔드 API 기반
- 기존 0.6.0 장착 API와 SQLite 테이블의 비파괴 호환 유지
- 실제 시험 정답이 아닌 가상 기능 확인 문제

현재 엔진은 교육용 논리 도통 모델입니다. 실제 전류·전압강하·접촉저항·아크·열·절연·차단기 트립 곡선·모터 RPM과 토크를 계산하지 않으며 실제 전기작업의 안전 판정 도구로 사용할 수 없습니다.

## 필요 환경

- Windows 10/11
- Python 3.11 이상
- Node.js 20 이상은 프런트엔드를 직접 다시 빌드할 때만 필요
- Microsoft Edge WebView2 Runtime

Windows 10/11의 최신 Edge 환경에는 WebView2가 일반적으로 포함되어 있습니다.

## 최초 설치

프로젝트 폴더에서 다음 파일을 실행합니다.

```bat
setup_windows.bat
```

이 스크립트는 `.venv` 생성과 Python 패키지 설치를 실행합니다. 배포본에는 빌드된 React 화면이 포함되어 있으므로 일반 사용자는 Node.js를 설치하지 않아도 됩니다. 설치 성공 또는 오류 내용을 확인할 수 있도록 마지막에 창이 유지됩니다.

프런트엔드를 직접 수정한 개발자만 다음 명령으로 npm 설치와 React 빌드를 다시 실행합니다.

```bat
setup_windows.bat -RebuildFrontend
```

설치가 실패하면 프로젝트 폴더에 생성되는 `setup.log`를 확인합니다.

## 데스크톱 모드

```bat
run_desktop.bat
```

실행기는 `127.0.0.1`의 빈 포트를 자동 선택하고 FastAPI가 준비된 후 전용 창을 엽니다. 창을 닫으면 로컬 서버도 종료됩니다.

데스크톱 모드의 사용자 DB와 로그는 기본적으로 다음 경로에 저장됩니다.

```text
%LOCALAPPDATA%\ElectricianSimulator
```

## 웹 모드

현재 PC에서만 접속:

```bat
run_web.bat
```

브라우저에서 `http://127.0.0.1:8000`을 엽니다.

같은 네트워크에 제한적으로 공개:

```bat
run_web.bat -Lan
```

LAN 모드는 `0.0.0.0:8000`에서 수신합니다. 다른 기기에서는 서버 PC의 내부 IP 주소로 접속해야 하며 Windows 방화벽 설정을 확인해야 합니다. 인증 기능이 들어가기 전에는 신뢰할 수 없는 네트워크나 인터넷에 공개하지 마십시오.

LAN 주소로 접속한 브라우저는 로컬 저장소에 생성된 식별자를 요청 헤더에 포함합니다. 서버는 사용자별 DB를 `%LOCALAPPDATA%\ElectricianSimulator\users` 아래에 분리하므로 서로 다른 브라우저의 회로 분석, 결선 초안, 제출기록과 동작시험 진행이 섞이지 않습니다. `127.0.0.1`과 Desktop 모드는 기존 `app.db`를 계속 사용해 과거 데이터와 호환됩니다. 이는 로컬 학습용 데이터 분리이며 로그인·권한 관리 기능은 아닙니다.

## 프런트엔드 개발 모드

첫 번째 터미널:

```bat
run_web.bat
```

두 번째 PowerShell 터미널:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_frontend_dev.ps1
```

Vite 개발 서버는 `/api` 요청을 `http://127.0.0.1:8000`으로 전달합니다.

## 테스트

Windows:

```bat
test_all.bat
```

개별 실행:

```powershell
.venv\Scripts\python.exe -m pytest
cd frontend
npm test
npm run build
```

전체 문제 참조 검사:

```powershell
.venv\Scripts\python.exe scripts\validate_problems.py
```

## 주요 폴더

```text
backend/    FastAPI, SQLite, 논리 동작시험 엔진
frontend/   React 공통 UI
desktop/    pywebview 실행기와 로컬 서버 생명주기
problems/   문제·답안 패키지
schemas/    문제·답안 JSON Schema
catalog/    공통 소켓·장치 유형
tools/      문제 패키지 검증 명령
scripts/    Windows 설치·실행·테스트 스크립트
```

## 상태 API

- `GET /api/health`: 서버와 버전 상태
- `GET /api/app-info`: 실행 모드, DB와 문제 폴더 준비 상태
- `GET /api/problems`: 유효한 문제 목록
- `GET /api/problems/{problem_id}`: 공개 문제 상세
- `POST /api/problems/reload`: 문제 폴더 다시 검색
- `GET /api/catalog/socket-types`: 8P·12P 공개 소켓 규격
- `GET /api/catalog/device-types`: 공개 장치 유형
- `GET /api/problems/{problem_id}/circuit-summary`: 정답을 제외한 회로 데이터 요약
- `GET /api/problems/{problem_id}/diagram`: 구조화 SVG 회로도
- `POST /api/problems/{problem_id}/circuit-attempts/submit`: 소켓번호 제출·채점
- `GET /api/problems/{problem_id}/circuit-progress`: 최근 제출 진행상태
- `GET /api/problems/{problem_id}/board`: 공개 제어함 배치
- `GET/PUT/DELETE /api/problems/{problem_id}/wiring-draft`: 결선 임시 저장
- `POST /api/problems/{problem_id}/wiring-attempts/submit`: 결선 제출·채점
- `GET /api/problems/{problem_id}/wiring-progress`: 결선 제출 진행상태
- `GET /api/problems/{problem_id}/operation-setup`: 공개 고정 기구 배치, 사용자 결선 및 동작시험 준비 상태
- `POST /api/problems/{problem_id}/operation-sessions`: 정상 결선 스냅샷으로 독립 동작시험 세션 생성
- `GET /api/operation-sessions/{session_id}`: 현재 동작 상태 조회
- `POST /api/operation-sessions/{session_id}/actions`: 전원·입력기구·시간 진행
- `POST /api/operation-sessions/{session_id}/reset`: 수동 시험 상태 초기화
- `POST /api/operation-sessions/{session_id}/run-check`: 비공개 조건으로 격리 자동 동작검사
- `DELETE /api/operation-sessions/{session_id}`: 동작시험 세션 종료
- `GET /api/problems/{problem_id}/operation-progress`: 최근 자동 동작검사 진행상태
- `GET/PUT/DELETE /api/free-circuits/{workspace_id}`: 사용자별 자유회로 정의·결선 저장
- `POST /api/free-circuits/{workspace_id}/sessions`: 정답 데이터 없이 공통 동작 엔진 세션 시작
- `GET/PUT/DELETE /api/problems/{problem_id}/mounting-draft`: 0.6.0 호환용 장착 임시 저장(새 UI에서 사용하지 않음)
- `POST /api/problems/{problem_id}/mounting-attempts/submit`: 0.6.0 호환용 장착 채점(새 UI에서 사용하지 않음)

API 응답에는 답안 데이터나 로컬 절대경로를 포함하지 않습니다.

## 문제 데이터

문제마다 다음 구조를 사용합니다.

```text
problems/problem_001/
├─ manifest.json
├─ problem.json
├─ answer.json
├─ schematic.svg
└─ assets/
```

내부 기능검증 회로 작성법은 `docs/problem-management.md`, 결선은 `docs/wiring-problem-authoring.md`, TB 자유 선택과 네트워크 채점은 `docs/wiring-network-grading.md`, 고정 기구 배치는 `docs/device-layout.md`, 동작 정의는 `docs/operation-simulation.md`에서 확인할 수 있습니다. Q-Net 공개문제 데이터는 일반 템플릿으로 추가하지 않고 공식 변경과 검증 절차가 있을 때만 갱신합니다. `docs/mounting-problem-authoring.md`는 0.6.0 호환 데이터 설명으로만 유지합니다.

```powershell
.venv\Scripts\python.exe -m tools.validate_problem problems\practice_001
.venv\Scripts\python.exe -m tools.validate_problem --all
```

## Windows 문제 해결

### BAT 명령이 잘리거나 인식되지 않는 경우

BAT 파일은 직접 설치 명령을 수행하지 않고 `scripts` 폴더의 PowerShell 파일을 호출합니다. 프로젝트 폴더 전체를 압축 해제한 후 BAT 파일을 실행하십시오.

### Python을 찾을 수 없는 경우

Python 3.11 이상을 설치하고 설치 과정에서 Python Launcher 또는 PATH 등록을 활성화합니다.

설치 여부는 명령 프롬프트에서 다음 명령으로 확인할 수 있습니다.

```bat
py -3 --version
```

### Node.js를 찾을 수 없는 경우

일반 실행에는 Node.js가 필요하지 않습니다. 프런트엔드를 수정하고 `-RebuildFrontend` 옵션을 사용할 때만 Node.js 20 이상을 설치합니다.

### 데스크톱 창이 열리지 않는 경우

Microsoft Edge WebView2 Runtime 설치 상태와 다음 로그를 확인합니다.

```text
%LOCALAPPDATA%\ElectricianSimulator\logs\app.log
```

### 8000번 포트가 사용 중인 경우

웹 모드는 기본적으로 8000번을 사용합니다. `APP_PORT` 환경변수로 변경할 수 있습니다. 데스크톱 모드는 빈 포트를 자동 선택하므로 이 문제가 발생하지 않습니다.

회로 모델은 `docs/circuit-data-model.md`, SVG 배치 데이터는 `docs/schematic-diagram.md`를 확인하십시오.

회로 분석·결선 화면 기능 확인은 `가상 소켓번호 입력 기능 확인`, 기본 논리 동작시험은 `자기유지·타이머 동작 기능 확인`을 선택합니다. 정·역회전은 `정·역회전 자기유지·인터록·EOCR 연습`, 보호 동작은 `자기유지·타이머·EOCR 보호 연습`을 선택합니다. 모두 프로그램 검증용 자체 제작 데이터이며 실제 Q-net 문제 또는 시험 정답으로 사용할 수 없습니다. `practice_001`은 정답이 미검증이므로 제출해도 채점하지 않습니다.

자유회로는 현재 공통 엔진·저장 API까지 구현되어 있습니다. 빈 제어함에서 기구를 배치하고 결선하는 사용자용 편집 화면은 아직 구현되지 않았으므로 Desktop/웹 화면에서 완전한 자유회로 제작 기능을 제공한다고 보지 않습니다.

## 동작시험 확인 순서

1. 기존 회로도 분석, 그래픽 결선, 요약 모드가 정상인지 확인합니다.
2. `정·역회전 자기유지·인터록·EOCR 연습`을 선택합니다.
3. 결선을 완료해 정상 제출하고 동작시험으로 이동합니다.
4. 전원을 켜고 PB1을 눌렀다가 놓아 MC1 자기유지와 정회전을 확인합니다.
5. 정회전 중 PB2를 눌러 MC2가 인터록으로 차단되는지 확인합니다.
6. PB0으로 정지한 뒤 PB2를 눌렀다가 놓아 MC2 자기유지와 역회전을 확인합니다.
7. 역회전 중 PB1을 눌러 MC1이 차단되는지 확인합니다.
8. `과부하 발생`을 눌러 EOCR 트립, 접촉기 해제, 모터 정지를 확인합니다.
9. 복귀 전 재기동이 차단되는지 확인하고 `EOCR 복귀` 후 다시 시작합니다.
10. 이벤트 기록 순서와 자동 동작검사 결과를 확인합니다.
11. 자동검사가 현재 수동 세션 상태를 변경하지 않는지 확인합니다.
12. 동작시험에서 전선과 기구를 수정할 수 없는지 확인합니다.
13. 재실행 후 학습 진행상태와 웹·데스크톱 화면이 같은지 확인합니다.

## 다음 개발 단계

향후 버전에서는 더 많은 자체 제작 시험형 문제, 복합 타이머 순서, 상세 안전 진단과 C++ 엔진 교체 인터페이스를 확장합니다. 현재 Python 엔진의 세션·그래프·상태 응답 계약은 유지할 수 있도록 분리되어 있습니다.
