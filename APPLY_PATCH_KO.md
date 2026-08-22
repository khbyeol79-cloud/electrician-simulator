# 0.11.0 → 0.11.1 패치 적용 안내

이 패치는 전기기능사 시퀀스 결선 시뮬레이터 `0.11.0` 전체본에만 적용합니다. 전체 프로젝트가 아니라 수정·추가 파일만 포함합니다.

## 적용 전

1. Web 서버와 Desktop 프로그램을 완전히 종료합니다.
2. 기존 `0.11.0` 프로젝트 폴더를 다른 위치에 통째로 복사해 백업합니다.
3. `%LOCALAPPDATA%\ElectricianSimulator`의 사용자 DB도 별도로 백업하는 것을 권장합니다.
4. 패치를 빈 폴더나 0.10.x 버전에 적용하지 마십시오.

## 적용 방법

1. 패치 ZIP을 임시 폴더에 압축 해제합니다.
2. `PATCH_MANIFEST.json`, `DELETED_FILES.txt`, 이 안내서와 테스트 보고서를 먼저 확인합니다.
3. ZIP 내부의 상대 경로를 유지한 채 모든 수정·추가 파일을 기존 `0.11.0` 프로젝트 루트에 덮어씁니다.
4. `DELETED_FILES.txt`에 기록된 이전 운영 빌드 파일만 삭제합니다.
5. 사용자 DB, 결선 초안, 승인 스냅샷, 자유회로 작업공간과 학습기록은 삭제하지 않습니다.
6. 이번 패치는 새 Python/npm 패키지를 추가하지 않으므로 기존 의존성을 그대로 사용할 수 있습니다.

Windows PowerShell에서 프로젝트 루트에 적용한 뒤 다음을 확인할 수 있습니다.

```powershell
.venv\Scripts\python.exe -m pytest backend\tests desktop\tests -q
.venv\Scripts\python.exe scripts\validate_problems.py
.venv\Scripts\python.exe scripts\run_actual_wiring_demo.py
cd frontend
npm test -- --run
npm run build
```

## 적용 후 확인

1. 화면 하단과 `GET /api/app-info`의 버전이 `0.11.1`인지 확인합니다.
2. 기존 문제의 회로도 분석·결선·동작시험과 기존 자유회로 작업공간이 열리는지 확인합니다.
3. 자유회로 동작시험 화면에 `기존 호환 모드` 또는 `실제 결선 모드`가 구분되어 표시되는지 확인합니다.
4. `scripts\run_actual_wiring_demo.py`가 자기유지, STOP, 정·역 상순서, 결상, EOCR 95-96 보호, 97-98 경보와 보호 우회 진단을 모두 통과하는지 확인합니다.
5. Desktop을 인터넷 연결 없이 실행하고 기존 SQLite 진행상태가 유지되는지 확인합니다.
6. LAN Web 모드에서는 서로 다른 브라우저의 작업공간과 동작 세션이 섞이지 않는지 확인합니다.

## 복원

문제가 발생하면 프로그램을 종료하고 적용 전 백업한 `0.11.0` 프로젝트 폴더와 사용자 DB를 복원합니다. `DELETED_FILES.txt`에 없는 파일이나 사용자 데이터를 임의로 삭제하지 마십시오.
