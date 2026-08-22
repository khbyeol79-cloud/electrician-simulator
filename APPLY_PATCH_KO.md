# 0.12.0 → 0.13.0 증분 패치 적용

이 압축은 수정·추가 파일만 포함한다. 반드시 기존 0.12.0 프로젝트 루트에 덮어쓴다.

1. 프로그램과 실행 중인 웹 서버를 종료한다.
2. 기존 프로젝트 폴더와 사용자 데이터 폴더를 백업한다.
3. ZIP 내용을 `electrician-simulator` 프로젝트 루트에 경로를 유지해 덮어쓴다.
4. `DELETED_FILES.txt`에 적힌 이전 빌드 파일을 삭제한다.
5. 기존 `.venv`, 사용자 SQLite DB, 자유회로 작업공간은 삭제하지 않는다.
6. 아래 명령으로 검증한다.

```powershell
.venv\Scripts\python.exe scripts\validate_problems.py
.venv\Scripts\python.exe scripts\run_qnet_18_smoke_test.py --problem 018
.venv\Scripts\python.exe -m pytest backend\tests desktop\tests -q
```

Node.js가 설치되어 있으면 추가로 실행한다.

```powershell
cd frontend
npm test -- --run
npm run typecheck
npm run build
```

0.13.0의 공식 18개는 원본 회로도 검토용 `draft`이다. 문제 선택과 1단계 원본 회로 확인은 가능하지만, 비공개 정답 네트워크와 동작 정의가 검증되기 전까지 공식 문제의 결선 채점·동작시험은 차단된다. 기존 자체 제작 문제와 자유회로는 계속 사용할 수 있다.

8P 릴레이/타이머의 전체 핀 정의가 공식 PDF 9쪽 근거로 바뀌었다. 기존 model_id는 유지되므로 작업공간을 다시 만들 필요는 없지만, 과거 임시 접점쌍 `6-3`을 사용한 자유회로는 실제 접점쌍 `1-3` 또는 `8-6`으로 수정해야 한다.
