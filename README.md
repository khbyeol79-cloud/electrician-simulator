# 전기기능사 시퀀스 결선 시뮬레이터

Windows 데스크톱 프로그램과 웹 브라우저에서 동일한 React 화면을 사용하는 전기기능사 실기 학습 프로그램입니다. 현재 저장소는 1단계 기반 구현으로, 공통 UI·FastAPI·SQLite·pywebview 실행 구조까지 포함합니다.

## 현재 구현된 기능

- React + TypeScript 공통 화면
- 회로도 분석·제어함 결선·기구 장착·동작시험 4단계 이동
- FastAPI 상태 API와 React SPA 제공
- SQLite 스키마 자동 초기화
- 데스크톱 실행 시 빈 포트 자동 선택
- pywebview 종료 시 로컬 FastAPI 서버 종료
- 웹/LAN 확장이 가능한 실행 설정
- 회전 로그와 한국어 오류 화면
- Python 및 프런트엔드 자동 테스트

실제 회로도, 8P·12P 소켓, 결선, 채점 및 동작시험은 아직 구현되지 않았습니다.

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
scripts/    Windows 설치·실행·테스트 스크립트
```

## 상태 API

- `GET /api/health`: 서버와 버전 상태
- `GET /api/app-info`: 실행 모드, DB와 문제 폴더 준비 상태

API 응답에는 답안 데이터나 로컬 절대경로를 포함하지 않습니다.

## 문제 데이터

문제마다 다음 구조를 사용할 예정입니다.

```text
problems/problem_001/
├─ manifest.json
├─ problem.json
├─ answer.json
├─ schematic.svg
└─ assets/
```

2단계에서 JSON Schema, 문제 검색 저장소, 답안 분리 서비스와 검증 명령을 구현합니다.

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

Node.js 20 이상을 설치한 후 새 명령 프롬프트를 열어 다시 실행합니다.

### 데스크톱 창이 열리지 않는 경우

Microsoft Edge WebView2 Runtime 설치 상태와 다음 로그를 확인합니다.

```text
%LOCALAPPDATA%\ElectricianSimulator\logs\app.log
```

### 8000번 포트가 사용 중인 경우

웹 모드는 기본적으로 8000번을 사용합니다. `APP_PORT` 환경변수로 변경할 수 있습니다. 데스크톱 모드는 빈 포트를 자동 선택하므로 이 문제가 발생하지 않습니다.

## 다음 개발 단계

2단계에서는 다음 항목을 구현합니다.

- `manifest.json`, `problem.json`, `answer.json` 스키마
- 문제 상태 `draft`, `reviewed`, `verified`
- 문제 검색 및 목록 API
- 정답 데이터의 일반 API 노출 방지
- 문제 패키지 검증 명령
- 샘플 문제와 문제 템플릿
