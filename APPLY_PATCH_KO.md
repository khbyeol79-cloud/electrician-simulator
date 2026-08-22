# 0.11.3 → 0.12.0 증분 패치 적용 안내

이 ZIP은 전체 프로젝트가 아니라 0.11.3에서 변경·추가된 파일과 완전한 React 운영 빌드만 포함합니다.

## 1. 적용 전 백업

1. 실행 중인 웹 서버와 데스크톱 프로그램을 종료합니다.
2. 현재 0.11.3 프로젝트 폴더 전체를 다른 위치에 복사합니다.
3. `%LOCALAPPDATA%\ElectricianSimulator` 사용자 DB를 별도로 백업합니다.
4. 프로젝트 `data`, 자유회로 작업공간, 결선 초안·승인 스냅샷과 학습기록을 삭제하지 않습니다.

## 2. 적용 위치

패치는 `backend`, `frontend`, `scripts`, `problems` 폴더가 보이는 프로젝트 루트에 덮어씁니다.

```powershell
$Project = "D:\project\elec\electrician-simulator"
$Patch = "D:\download\electrician-simulator-0.11.3-to-0.12.0-patch.zip"
$PatchTemp = Join-Path $env:TEMP "electrician-0.12.0-patch"

if (Test-Path $PatchTemp) { Remove-Item $PatchTemp -Recurse -Force }
Expand-Archive -Path $Patch -DestinationPath $PatchTemp -Force
Copy-Item -Path (Join-Path $PatchTemp "*") -Destination $Project -Recurse -Force
```

운영 빌드의 해시 파일명이 변경되므로 패치를 덮어쓴 뒤 `DELETED_FILES.txt`에 적힌 과거 자산만 삭제합니다.

```powershell
$DeleteList = Get-Content (Join-Path $PatchTemp "DELETED_FILES.txt")
foreach ($RelativePath in $DeleteList) {
    $Target = Join-Path $Project $RelativePath
    if (Test-Path $Target) { Remove-Item $Target -Force }
}
```

## 3. 적용 후 테스트

```powershell
cd $Project
.venv\Scripts\python.exe -m pytest backend\tests desktop\tests -q
.venv\Scripts\python.exe scripts\run_actual_wiring_demo.py
.venv\Scripts\python.exe scripts\run_basic_board_demo.py
.venv\Scripts\python.exe scripts\run_empty_board_demo.py
.venv\Scripts\python.exe scripts\validate_problems.py

cd frontend
npm test -- --run
npm run typecheck
npm run build
```

`npm`을 찾을 수 없으면 Node.js LTS를 설치한 뒤 새 PowerShell에서 프런트엔드 명령을 실행합니다. 패치에는 이미 검증한 `frontend/dist`가 포함되므로 일반 실행에는 npm이 필요하지 않습니다.

## 4. 핵심 수동 확인

1. 화면 하단 버전이 `0.12.0`인지 확인합니다.
2. 기존 기본보드와 과거 자유회로가 그대로 열리는지 확인합니다.
3. 새 자유회로에서 `기본보드`, `빈보드` 두 선택지만 보이는지 확인합니다.
4. 빈보드에 TB5·TB6만 있고 중앙 장착칸이 비어 있는지 확인합니다.
5. 팔레트에서 내부 기구를 선택해 빈 장착칸에 설치합니다.
6. 외부 전원·PB·표시등·모터가 외부 기구선 영역에 추가되는지 확인합니다.
7. 기구 이동 후 instance ID와 연결 전선이 유지되는지 확인합니다.
8. 연결된 기구 삭제 시 확인창 후 관련 전선이 함께 삭제되는지 확인합니다.
9. 기구 추가·이동·삭제와 전선을 Undo/Redo한 뒤 다시 열어 복원되는지 확인합니다.
10. 전원 없는 빈보드의 동작시험이 한국어 안내로 차단되는지 확인합니다.
11. `docs/empty-board-manual-test-0.12.0.md`의 릴레이·PB·타이머 결선을 시험합니다.
12. 두 데모 종료 뒤 `WinError 32` 없이 PowerShell 프롬프트로 정상 복귀하는지 확인합니다.
13. 빈보드에 내부 기구를 설치한 뒤 기구 단자와 TB 단자를 연결해 화면 중단 없이 전선이 표시되는지 확인합니다.

## 5. 되돌리기

문제가 있으면 프로그램을 종료하고 백업한 0.11.3 프로젝트를 복원합니다. 사용자 DB는 삭제하거나 빈 DB로 덮어쓰지 않습니다. SQLite 9의 추가 컬럼은 기존 데이터에 영향을 주지 않지만, 되돌릴 때도 백업한 사용자 DB를 함께 보존하는 것이 안전합니다.
