# 0.11.1 자동 검증 결과

검증 일자: 2026-08-22 (Asia/Seoul)

## 실행 결과

| 구분 | 명령 | 결과 |
|---|---|---|
| 백엔드·Desktop | `.venv/bin/python -m pytest backend/tests desktop/tests -q` | 131개 통과, 실패 0개 |
| 프런트엔드 | `frontend/node_modules/.bin/vitest run --maxWorkers=1` | 6개 파일, 55개 통과, 실패 0개 |
| TypeScript | `frontend/node_modules/.bin/tsc -b` | 통과 |
| React 운영 빌드 | `frontend/node_modules/.bin/vite build` | 62 modules, 성공 |
| 문제·카탈로그·참조 | `PYTHONPATH=backend .venv/bin/python scripts/validate_problems.py` | 정상 5개, 오류 0개, 경고 1개 |
| 실제 결선 간단 시험 | `.venv/bin/python scripts/run_actual_wiring_demo.py` | 모든 시나리오 통과 |
| 패치 적용 복원 시험 | 0.9.4 전체본에 0.10.0·0.10.1·0.11.0 패치를 순서대로 적용한 임시 복사본에 0.11.1 패치 적용 | 버전 0.11.1, Python 131개 통과 |
| 비 UTF-8 기본 로캘 | `LC_ALL=C PYTHONUTF8=0 .venv/bin/python -m pytest backend/tests/test_actual_wiring_interlocks.py -q` | 인터록 테스트 3개 통과 |

문제 검사기의 경고 1개는 `practice_001/answer.json`의 기존 미검증 답안 상태다. 별도 정책 경고로 검증된 Q-Net 공식 문제가 아직 `0/18`임을 확인했다. 자체제작 문제 5개를 공식 공개문제로 승격하거나 변경하지 않았다.

## 0.11.1에서 추가 확인한 핵심 시나리오

- 런타임 구성 결과의 결정성·멱등성 및 입력 정의 비변경
- 존재하지 않는 모델과 기구 종류 불일치 거부
- MC 코일 상태에 따른 주접점 3개와 보조접점 전환
- 실제 보조 NO 접점에 의한 자기유지와 STOP 복귀
- 실제 NC 경로에 의한 전기적 인터록 및 우회 진단
- 전기 접점과 별도인 기계적 인터록의 동시 투입 차단
- EOCR 정상/트립 시 95-96·97-98 상태 전환
- EOCR 97-98 경보 표시등 점등
- EOCR 95-96 우회 시 강제 정지하지 않고 위험 진단
- 실제 3상 연결 순서에 따른 정회전·역회전
- 결상, 상간 단락, 동시 접촉기 투입 진단
- 기존 `legacy_assisted` 문제와 저장 형식 호환
- 정답·`expected_nets`가 동작 엔진/API에 노출되지 않음
- 사용자별 자유회로 작업공간과 동작 세션 분리
- 정적 운영 빌드 제공과 Desktop 로컬 서버 생명주기

## 환경상 수동 확인이 필요한 항목

자동 테스트는 Linux 개발 환경과 FastAPI/React 테스트 런타임에서 수행했다. 실제 Windows 10/11의 pywebview 창, WebView2, LAN의 서로 다른 물리 기기, 인터넷을 끊은 상태의 EXE 실행은 이 환경에서 직접 조작하지 못했으므로 사용자 수동 확인 대상이다.

패치 적용 복원 시험의 0.11.0 임시본은 보관된 0.9.4 전체본과 후속 패치들로 재구성했다. 과거 배포본에 포함되지 않았던 개발용 임시 산출물은 작업 전 개발 폴더의 전체 해시 기준과 차이가 있었지만, 0.11.1 패치의 34개 payload 해시와 삭제 목록을 적용한 뒤 전체 Python 회귀 테스트가 통과했다.

## 알려진 제한

- 현재 문제 5개와 기존 자유회로 시작 보드 3종은 저장 데이터 호환을 위해 `legacy_assisted`가 기본이다.
- 실제 결선 모드는 새 명시적 `behavior_model_id`가 있는 자체제작 회로에서 사용한다.
- `magnetic_contactor_12p_training`, `eocr_12p_training`, `limit_switch_nc`는 계속 `unverified`다.
- 실제 전압·전류·접촉저항·단락전류·RPM·토크는 계산하지 않는다.
