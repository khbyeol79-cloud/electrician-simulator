# 회로도 분석 참고 자료·사용법 추가 검증

## 작업 범위

- 기준 브랜치: `feature/qnet-all-wiring-capture`
- 작업 시작 커밋: `fffabd970df09028f0ffa95a107c0e559dbd90d0` (시작 시 작업 트리 깨끗함)
- 공개문제 001~018의 회로도 분석에 동작사항(원본 PDF 8쪽), 기구 내부결선도(9쪽) 탭 추가.
- 접점·코일을 선택하면 슬롯번호 입력창과 하단 입력예시 사이에 해당 기구의 원본 내부결선도 표시. 그림을 클릭하면 확대 팝업으로 확인.
- EOCR, MC1/MC2, X/X1/X2, T/T1/T2, FR, FLS, SS를 해당 원본 그림과 연결. 수동으로 추가한 표시도 기구 선택 가능.
- 상단 초기화 오른쪽에 사용법 버튼 추가. 문제 선택, 분석, 결선, 동작시험, 저장, 공용 PC 사용을 안내.
- 짧은 화면에서 입력예시가 잘리지 않도록 영역을 분리하고 양쪽 단자 입력란을 나란히 배치.

## 원본 근거 및 제한

- 원본 디렉터리: `D:/project/elec/전기기능사 공개문제, 2025-08-04`
- 각 PDF 8·9쪽을 PNG로 렌더링. 9쪽의 그림 영역과 캡션을 기준으로 개별 기구 그림을 잘라 사용했으며 새 내부회로를 그리거나 추측하지 않았다.
- 001~009에는 FR/FLS/SS 그림이 있고 010~018에는 없다. 문제별 구성 차이를 유지했다.
- 18개 페이지 7 원본 회로도를 시각적으로 대조하여 기존 클릭 위치 643곳에 기구 이름을 연결했다. 슬롯번호 정답이나 결선망을 추가한 것이 아니다.
- `catalog/qnet_analysis_references.json`에 원본 PDF SHA-256, 이미지 SHA-256, 페이지·크기·자르기 좌표 기록. 기존 공식 자료 인벤토리 해시와 일치하는지 검사.
- 공개 자료 이미지 171개를 각 문제의 `study-references`에 저장. 배포 ZIP 생성기에도 포함했다. 실행 PC에서는 원본 PDF나 PyMuPDF가 필요 없다.
- BZ·표시등·PB 등 별도 내부결선도 그림이 없는 기구는 없다고 안내한다. 서버 연결 실패는 이 안내와 구분하여 다시 불러오기를 제공한다.
- 기존 엔진, operation_tests, expected_nets, 문제 정의, 사용자 답안 및 기존 저장 데이터는 수정하지 않았다.

## 실행한 검증

PowerShell에서 저장소 루트를 기준으로 실행했다. 기존 TEMP pytest 폴더의 접근 문제를 피하기 위해 매번 별도 임시 디렉터리를 사용했다.

| 검증 | 명령 | 결과 |
|---|---|---|
| 관련 백엔드·공식 자료·배포 | `.venv/Scripts/python.exe -X utf8 -m pytest backend/tests/test_analysis_references.py backend/tests/test_qnet_public_sources.py backend/tests/test_lan_transfer.py -q --basetemp <고유 TEMP 경로>` | 15개 통과 |
| 관련 화면·뷰포트·분석 | `npm.cmd test -- --run src/tests/AnalysisReferences.test.tsx src/tests/DiagramViewport.test.tsx src/tests/CircuitDiagnostics.test.tsx` (frontend) | 37개 통과 |
| Python 전체 | `.venv/Scripts/python.exe -X utf8 -m pytest backend/tests --basetemp <고유 TEMP 경로> -o addopts='' -q` | 605개 통과, 366.17초 |
| 문제 검사 | `.venv/Scripts/python.exe -X utf8 scripts/validate_problems.py` | 정상 23, 제외 0, 오류 0, 기존 unverified 경고 19 |
| frontend 전체 | `npm.cmd test` (frontend) | 19개 파일, 153개 테스트 통과 |
| TypeScript | `npm.cmd run typecheck` (frontend) | 통과 |
| production build | `npm.cmd run build` (frontend) | 통과; dist는 빌드로만 갱신 |
| diff 검사 | `git diff --check` | 통과 |

Python의 기존 Starlette/httpx 사용 중단 예정 경고 1개는 이번 기능 오류가 아니다. 공식 정답 미검증 상태를 이 화면 기능 추가로 변경하지 않았다.

## 실제 브라우저 수동 확인

운영 중인 LAN 서버와 사용자 DB 대신 별도의 TEMP 데이터와 루프백 8024 포트로 검증했다. 검증 서버는 정상 종료했으며 운영 서버는 중지하거나 재시작하지 않았다.

| 확인 항목 | 결과 |
|---|---|
| 문제 선택 창에서 001~018을 각각 선택하고 동작사항·내부결선도 전환 | 18/18, 해당 문제의 원본 URL로 전환 |
| 001의 EOCR 가로 접점, X 접점 클릭 | 해당 기구 자동 선택 및 내부결선도 표시 |
| MC1·EOCR·T·X·FR·FLS·SS 선택 | 각 원본 그림 표시 |
| BZ 선택 | 내부결선도 없음 안내, 허구의 그림 없음 |
| EOCR·FLS 이미지 확대 팝업 | 단자번호와 그림 확인, Escape 닫기 |
| 동작사항 확대·드래그 | 확대율 및 이동 좌표 변화 확인 |
| 입력한 EOCR 10/4의 재로딩·탭 전환 | 기존 번호 유지 |
| 사용법 | 초기화 다음 위치, 6개 안내 항목, 팝업·Escape 닫기 확인 |
| 1920×940, 1536×760, 1280×650, 2560×1300 | 메뉴 접근 및 참고 자료 배치 확인. 1280×650에서 하단 예시 잘림을 발견해 수정 후 재검증 |
| 1280×650 최종 사이드바 | 전체 높이와 scrollHeight 모두 426px, 예시가 패널 안에 유지됨. 작은 그림은 클릭 확대 가능 |
| 브라우저 console | error/warn 없음 |

원본 렌더링 9쪽에서 추출된 서로 다른 기구 그림 10종도 따로 열어 잘림과 캡션을 시각적으로 확인했다. 모든 문제의 모든 기구를 브라우저에서 하나씩 클릭한 것은 아니며, 전체 클릭 위치의 개수·기구 존재와 기존 좌표 불변은 자동 테스트로 검사했다.

## 주요 변경 파일

- backend: `app/api/problems.py`, `app/repositories/problem_repository.py`, `tests/test_analysis_references.py`
- frontend: `pages/CircuitAnalysisPage.tsx`, `components/circuit/AnalysisReferencePage.tsx`, `components/circuit/DeviceInternalReference.tsx`, `components/UsageHelp.tsx`, `components/Header.tsx`, `components/WorkspaceDialog.tsx`
- frontend 보조: `api/client.ts`, `features/circuit/analysisAnnotations.ts`, `features/circuit/contactDeviceOrder.json`, `styles/responsive.css`, `tests/AnalysisReferences.test.tsx`
- 자료·배포: `scripts/build_analysis_references.py`, `scripts/build_lan_release.py`, `catalog/qnet_analysis_references.json`, 각 공개문제의 `study-references/*.png`

## 적용 안내

새 API 경로를 사용하므로 기존 서버 프로세스는 안전한 종료·백업 후 재시작하고 브라우저를 새로고침해야 한다. 다른 PC로 옮길 때는 배포 ZIP 생성 BAT를 다시 실행해 새 코드와 참고 이미지가 포함된 ZIP을 사용한다. 계정·학습 기록 백업은 종전처럼 별도로 이전한다.
