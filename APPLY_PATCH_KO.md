# 0.11.2 → 0.11.3 증분 패치 적용 안내

이 ZIP은 전체 프로젝트가 아니라 0.11.2에서 변경되거나 추가된 파일과 React 운영 빌드만 포함합니다.

## 1. 적용 전 백업

1. 실행 중인 웹 서버와 데스크톱 프로그램을 종료합니다.
2. 현재 0.11.2 프로젝트 폴더 전체를 다른 위치에 복사합니다.
3. `%LOCALAPPDATA%\ElectricianSimulator` 사용자 DB를 별도로 백업합니다.
4. 프로젝트의 `data`, 자유회로 작업공간, 승인 결선과 사용자 기록을 삭제하지 않습니다.

## 2. 적용 위치

패치는 `backend`, `frontend`, `scripts`, `problems` 폴더가 보이는 프로젝트 루트에 덮어씁니다.

```powershell
$Project = "D:\project\elec\electrician-simulator"
$Patch = "D:\download\electrician-simulator-0.11.2-to-0.11.3-patch.zip"
$PatchTemp = Join-Path $env:TEMP "electrician-0.11.3-patch"

if (Test-Path $PatchTemp) { Remove-Item $PatchTemp -Recurse -Force }
Expand-Archive -Path $Patch -DestinationPath $PatchTemp -Force
Copy-Item -Path (Join-Path $PatchTemp "*") -Destination $Project -Recurse -Force
```

운영 빌드의 해시 파일명이 변경되었으므로, 패치를 덮어쓴 뒤 아래의 0.11.2 자산 두 개만 삭제합니다. 다른 파일이나 폴더는 삭제하지 않습니다.

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
.venv\Scripts\python.exe scripts\validate_problems.py

cd frontend
npm test -- --run
npm run typecheck
npm run build
```

`npm`을 찾을 수 없다는 오류가 나오면 Node.js LTS를 설치하고 새 PowerShell 창에서 다시 실행합니다.

## 4. 적용 후 핵심 확인

1. 화면 하단 버전이 `0.11.3`인지 확인합니다.
2. 기존 자유회로 작업공간이 그대로 열리는지 확인합니다.
3. 전선을 선택하고 `Delete`를 눌러 해당 전선만 삭제되는지 확인합니다.
4. `실행 취소`로 삭제된 전선이 복원되는지 확인합니다.
5. 편집 뒤 `자동 저장됨`이 표시되는지 확인합니다.
6. 수동 저장 없이 작업공간을 다시 열어 전선이 복원되는지 확인합니다.
7. 오른쪽 패널 너비와 글자 가독성을 확인합니다.
8. 왼쪽 아래 문제 정보 카드가 제거되었는지 확인합니다.
9. 회로도 분석에만 확대·축소 버튼이 남아 있는지 확인합니다.
10. `docs/ui-manual-test-0.11.3.md` 순서로 화면 크기와 자동 맞춤을 확인합니다.

## 5. 되돌리기

문제가 있으면 프로그램을 종료한 뒤 백업한 0.11.2 프로젝트 폴더를 복원합니다. 사용자 DB는 삭제하거나 빈 DB로 덮어쓰지 않습니다.
