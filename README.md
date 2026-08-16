# 전기기능사 시퀀스 결선 시뮬레이터

Windows 데스크톱 프로그램과 웹 브라우저에서 동일한 React 화면을 사용하는 전기기능사 실기 학습 프로그램입니다. 현재 버전은 0.6.1이며 데이터 기반 회로도 분석, 제어함 결선, 동작시험 준비 화면을 포함합니다.

0.6.1에서는 실제 시험 문제지에 기구 위치가 주어진다는 점을 반영해 별도의 기구 장착 채점 단계를 제거했습니다. 회로도 분석 → 제어함 결선 → 동작시험의 3단계로 진행하며, 결선 제출 후 문제의 공개 고정 배치에 따라 릴레이와 타이머가 자동 삽입된 읽기 전용 화면을 표시합니다.

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
- 회로도 분석 결과를 결선 화면에서 확인하는 확대·이동 참고창
- 결선 제출 성공 후 동작시험 화면 자동 이동
- 문제지 공개 조건인 8P·12P 릴레이·타이머 고정 배치
- 사용자 결선과 고정 기구를 함께 표시하는 읽기 전용 동작시험 준비 화면
- 기존 0.6.0 장착 API와 SQLite 테이블의 비파괴 호환 유지
- 실제 시험 정답이 아닌 가상 기능 확인 문제

실제 전기적 회로 계산과 최종 동작시험은 아직 구현되지 않았습니다.

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

## 주요 폴더

```text
backend/    FastAPI, SQLite, 추후 회로 엔진
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

작성법은 `docs/problem-management.md`, 결선은 `docs/wiring-problem-authoring.md`, 고정 기구 배치는 `docs/device-layout.md`에서 확인할 수 있습니다. `docs/mounting-problem-authoring.md`는 0.6.0 호환 데이터 설명으로만 유지합니다. 문제 검증 명령은 다음과 같습니다.

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

기능 확인은 문제 선택창에서 `가상 소켓번호 입력 기능 확인`을 선택합니다. 이 문제의 VR1은 실제 장치가 아니며 실제 시험 정답으로 사용할 수 없습니다. `practice_001`은 정답이 미검증이므로 제출해도 채점하지 않습니다.

## 다음 개발 단계

다음 0.7.0에서는 회로도 분석과 제출된 결선을 이용해 전원 투입, 푸시버튼, 릴레이 접점, 타이머, 표시등과 모터 상태를 계산하는 동작시험을 구현합니다. 동작시험 입력은 `device_layout.fixed_placements`, 사용자 결선, 회로 정의를 사용하며 사용자가 작성했던 장착 답안은 사용하지 않습니다.
