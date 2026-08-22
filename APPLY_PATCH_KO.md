# 0.11.1 → 0.11.2 패치 적용 안내

이 패치는 전기기능사 시퀀스 결선 시뮬레이터 `0.11.1` 전체본에만 적용한다. 전체 프로젝트가 아니라 수정·추가 파일과 변경된 React 운영 빌드만 포함한다.

## 적용 전

1. Web 서버와 Desktop 프로그램을 완전히 종료한다.
2. 기존 `0.11.1` 프로젝트 폴더를 다른 위치에 통째로 복사한다.
3. `%LOCALAPPDATA%\ElectricianSimulator`과 프로젝트의 기존 사용자 DB를 별도로 백업한다.
4. 패치를 빈 폴더나 0.11.0 이하 버전에 바로 적용하지 않는다.

## 적용 방법

1. 패치 ZIP을 임시 폴더에 압축 해제한다.
2. `PATCH_MANIFEST.json`, `DELETED_FILES.txt`, 이 안내서와 테스트 보고서를 확인한다.
3. 압축 내부 상대 경로를 유지하여 모든 수정·추가 파일을 기존 0.11.1 프로젝트 루트에 덮어쓴다.
4. `DELETED_FILES.txt`에 적힌 이전 React 해시 파일만 삭제한다.
5. 사용자 DB, 결선 초안, 승인 스냅샷, 자유회로 작업공간과 학습기록은 삭제하지 않는다.
6. 이번 패치는 Python/npm 의존성을 추가하지 않으므로 기존 가상환경을 그대로 사용할 수 있다.

Windows PowerShell에서 프로젝트 루트에 적용한 뒤 다음을 실행한다.

```powershell
.venv\Scripts\python.exe -m pytest backend\tests desktop\tests -q
.venv\Scripts\python.exe scripts\validate_problems.py
.venv\Scripts\python.exe scripts\run_actual_wiring_demo.py
.venv\Scripts\python.exe scripts\run_basic_board_demo.py
cd frontend
npm test -- --run
npm run typecheck
npm run build
```

Node.js가 없는 일반 사용자는 포함된 `frontend/dist`로 프로그램을 실행할 수 있으므로 npm 명령은 생략하고 Python 시험 및 화면 수동 확인을 진행한다.

## 적용 후 핵심 확인

1. 화면 하단과 `GET /api/app-info` 버전이 `0.11.2`인지 확인한다.
2. 기존 문제의 회로도 분석·결선·동작시험과 기존 자유회로 작업공간이 그대로 열리는지 확인한다.
3. 자유회로 신규 생성 화면에서 템플릿 드롭다운이 사라지고 이름 입력란과 `기본보드로 만들기`만 표시되는지 확인한다.
4. 같은 이름으로 두 작업공간을 만들었을 때 서로 다른 ID와 결선을 가지는지 확인한다.
5. 기본보드의 초기 전선이 0개이고 `실제 결선 모드`로 표시되는지 확인한다.
6. `docs/basic-board-manual-test-0.11.2.md`의 X1 자기유지, T1 지연 GL, MC1·EOCR·M1 결선을 각각 별도 작업공간에서 시험한다.
7. `scripts\run_basic_board_demo.py` 마지막에 `모든 기본보드 시험이 통과했습니다.`가 표시되는지 확인한다.
8. Desktop 인터넷 차단 실행과 LAN Web의 서로 다른 브라우저 사용자 분리는 실제 Windows 환경에서 확인한다.

## 복원

문제가 발생하면 프로그램을 종료하고 적용 전 백업한 0.11.1 프로젝트 폴더와 사용자 DB를 복원한다. `DELETED_FILES.txt`에 없는 파일이나 사용자 데이터를 삭제하지 않는다.
