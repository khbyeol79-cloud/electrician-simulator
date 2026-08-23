# Test Results - Q-Net 010 evidence audit

검사일: 2026-08-24 (Asia/Seoul)

기준: `ca87754f320be5c73d05bfb1dfaf6cc7cf5e3e7a`, tag `v0.13.0-stable-fuse`

## 새 환경 기준선

- 기존 `.venv`를 프로젝트 절대경로 확인 후 삭제했다.
- Python 3.14.6으로 `.venv`를 새로 생성했다.
- `backend/requirements.txt`를 새로 설치하고 `pip check`를 통과했다.

## 실행 결과

| 검사 | 명령 | 결과 |
| --- | --- | --- |
| 백엔드 전체 | `.venv\Scripts\python.exe -m pytest` | 151 passed, warning 1 |
| 문제 패키지 | `.venv\Scripts\python.exe scripts\validate_problems.py` | 23 packages, errors 0, warnings 19 |
| 프런트엔드 | `npm test` | 7 files, 67 passed |
| TypeScript | `npm run typecheck` | PASS |
| 운영 빌드 | `npm run build` | PASS, 63 modules transformed |
| 공식 전체 스크립트 | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test_all.ps1` | PASS |

경고 19건은 공식 문제 답안의 `unverified` 상태에 관한 의도된 경고다. Python 경고 1건은 Starlette TestClient의 httpx 호환성 deprecation이며 실패가 아니다.

## Q-Net 010 결정

기능 코드는 수정하지 않았다. 사용자 제공 현장 사진으로 한 홀더의 좌·우 퓨즈 두 개와 네 결선점 구조를 추가 확인했다. `1-2`, `3-4`는 실기 준비자들의 구현 명명 관례로 기록했지만 Q-Net 공식 단자 번호 문서가 아니므로 정답 네트워크와 동작시험을 작성하지 않았다. `draft/unverified` 차단 상태가 정상이다.
