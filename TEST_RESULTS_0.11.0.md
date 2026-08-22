# 0.11.0 테스트 결과

## 자동 검사

- 백엔드 테스트: `113 passed`, 경고 1개
- Desktop 실행기 테스트: `2 passed`
- Python 전체 테스트: `115 passed`, 경고 1개
- 프런트엔드 테스트: `6 files, 54 tests passed`
- TypeScript 검사: `tsc -b` 통과
- React 운영 빌드: 성공, 62개 모듈 변환
- Python 구문 검사: `compileall` 통과
- 문제·카탈로그 데이터 검사: 정상 5개, 제외 0개, 오류 0개, 경고 1개

Python 경고는 기존 FastAPI TestClient의 `httpx` 호환성 폐기 예정 안내다. 문제 검사 경고는 기존 `practice_001` 정답이 `unverified`인 상태다. 이번 변경으로 발생한 오류는 아니다.

Q-Net 정책 검사 결과는 검증된 공식 공개문제 데이터 `0/18`이다. 공식 자료가 없는 문제를 임의로 생성하거나 기존 자체제작 문제를 공식 문제로 표시하지 않았다.

## 공통 기구 동작 카탈로그 검사

- 16개 동작 모델 정상 로딩
- device type·socket type 상호 참조
- model·terminal·pin·coil·contact·설정 키 중복 차단
- 소켓 범위를 벗어난 핀 차단
- coil·contact·timer·intrinsic connection의 존재하지 않는 로컬 키 차단
- NO·NC 접점 기본 상태 모순 차단
- capability와 실제 동작 정의의 모순 차단
- 인스턴스에서 충돌하는 ID suffix 차단
- 특정 TB5·TB6 번호와 정답 전용 필드 차단
- 손상된 파일의 파일명·모델·필드 경로 포함 한국어 오류 확인

## 기구 인스턴스 생성기 검사

- 동일 입력의 결정적 ID 생성
- 동일 모델 X1·X2의 단자·코일·접점 ID 비충돌
- 8P 릴레이 코일 2-7과 NO 접점 6-3 fragment
- 타이머 지연시간 설정과 계시 접점 fragment
- MC의 `general` 역할과 문제별 START·Motor 관계 미포함
- PB·LS OperationControl fragment
- 램프 색상 instance setting
- EOCR 보호 대상과 보호 접점의 composer 지연 처리
- 모터 정·역 역할의 composer 지연 처리
- 잘못된 설정·범위·소켓 호환성 차단
- 카탈로그 원본 불변성
- 보드 위치가 모델에 하드코딩되지 않음

## 기존 기능 회귀

- 기존 device-types·socket-types API 유지
- 새 device-behaviors 목록·단일 조회 API
- 공개 응답의 `expected_nets`, `wiring_connections`, 특정 TB 번호 비노출
- 기존 문제 5개 로딩
- TB 번호 독립 Net 채점 테스트 유지
- 기존 자유회로 3종 생성·저장·복원·동작 세션 테스트 유지
- PB·자기유지·Relay·Timer·MC·인터록·EOCR·Lamp·Motor 테스트 유지
- 기존 SQLite와 사용자별 데이터 분리 테스트 유지
- Web SPA 정적 파일 제공 테스트 유지
- Desktop 빈 포트·로컬 서버 수명주기 테스트 유지

## 운영 빌드

```text
frontend/dist/index.html
frontend/dist/assets/index-BUK8lGZO.css
frontend/dist/assets/index-DZLDjMmg.js
```

기존 `frontend/dist/assets/index-ChnLszOu.js`는 새 JavaScript 번들로 교체되어 패치 적용 시 삭제해야 한다.

## 수동 확인 필요

자동 테스트는 데이터·API·엔진 회귀와 빌드를 검증했다. 실제 Windows 환경에서는 다음을 직접 확인해야 한다.

1. 화면 하단과 `/api/app-info`의 버전 `0.11.0`
2. 기존 문제 선택·회로도 분석·결선·동작시험
3. 다른 TB 번호의 동등 결선 정답 처리
4. PB·자기유지·STOP·타이머·정역·인터록·EOCR 동작
5. 자유회로 기존 3개 시작 보드와 저장 작업공간 복원
6. `/api/catalog/device-behaviors` 응답과 정답 비노출
7. Web·Desktop 결과 비교
8. 인터넷 연결을 끊은 Desktop 핵심 기능
