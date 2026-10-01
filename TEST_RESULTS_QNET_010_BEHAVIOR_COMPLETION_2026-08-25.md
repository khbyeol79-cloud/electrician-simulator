# Q-Net 010 behavior workflow completion test results

- Date: 2026-08-25
- Branch: `feature/qnet-010-behavior-validation`
- Base commit: `fc3c8a77a80c1770a674feecb338a2abf09965a3`
- Work commit: the follow-up commit containing this document; see final handoff report
- Python: 3.12.13
- Node.js: v24.19.0
- npm: 11.17.0

## Stage gates

| Stage | Scope | Command summary | Result |
|---|---|---|---:|
| Baseline | backend, desktop, packages, frontend, build | `scripts/test_all.ps1` | Python 207; frontend 71; packages 23/0 errors; build pass |
| A | PB NO/NC, self-hold, STOP, 8P group swap | focused `pytest` | 8 passed |
| B | timer 999/1000ms and STOP/EOCR/power reset | focused `pytest` | 4 passed |
| C | MC, motors, lamps, interlocks | focused `pytest` | 6 passed |
| D | EOCR supply, trip, alarm, manual reset | focused `pytest` | 5 passed |
| E | dual fuse isolation, individual faults, legacy loading | focused `pytest` | 9 passed |
| Candidate/API | private candidate, SQLite restart, five scenarios, non-exposure | `pytest backend/tests/test_qnet_010_private_validation.py -q` | 40 passed |
| Frontend | scenario cards and operation controls | `npm test -- --run src/tests/OperationPage.test.tsx` | 10 passed |
| Focused regression | Q-Net 010, user audit, shared engine, bypasses, fuse | focused `pytest` | 72 passed |
| Readiness | Q-Net 010 implementation readiness | `scripts/check_qnet_010_readiness.py` | 20 pass, 0 blocked |

## Final full gate

```powershell
$env:PYTEST_ADDOPTS='--basetemp=D:/project/elec/qnet-18/pytest-completion-final-20260825 -p no:cacheprovider'
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test_all.ps1
```

- Python: 208 passed, one existing Starlette/httpx deprecation warning
- Problem validator: 23 loaded, 0 errors, 19 intended draft/unverified warnings
- Frontend Vitest: 7 files, 71 passed
- TypeScript: passed
- Vite production build: 64 modules
- Production assets: `index-I0x59HvI.css`, `index-CgKLvrwX.js`

## Five behavior scenarios

| Scenario | Shared actual-wiring evidence | Result |
|---|---|---:|
| PB1 | X1 hold, LS1, T1 boundary, MC1, RL/WL, M1 | satisfied |
| PB2 | X2 hold, LS2, T2 boundary, MC2, GL/WL, M2 | satisfied |
| STOP | both control paths drop; timers stopped/0ms; no automatic restart | satisfied |
| EOCR | A1-A2 powered; trip, motor stop, YL, manual reset; no automatic restart | satisfied |
| Power off/restore | coils and timers reset; motors stop; no automatic restart | satisfied |

Five of five means only that the private development candidate reproduces the five defined behaviors in the current shared engine. It is not an answer, score or pass/fail decision.

## Error and privacy regression

- Missing, wrong, unknown, duplicate, self-connected and over-capacity wiring remains rejected or unsatisfied as appropriate.
- Phase/return short and merged fuse channels block power.
- STOP, fuse, EOCR, timer and MC/interlock bypass variants do not satisfy the affected requirements.
- Public API responses, frontend source/build and QA logs contained zero private candidate markers, private Net IDs or private operation-test IDs.
- All browser and automated tests used isolated temporary data; no existing user SQLite or workspace was changed.
