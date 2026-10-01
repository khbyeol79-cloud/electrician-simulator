# Q-Net 010 behavior workflow manual verification

- Date: 2026-08-25
- Build: production frontend served by local FastAPI on `http://127.0.0.1:8010`
- Browser: Codex in-app browser
- Data: isolated temporary SQLite directory, deleted after verification

| Flow | Actual result |
|---|---|
| Select Q-Net 010 | circuit analysis opened and current problem remained selected |
| Analysis autosave | memo/device/terminal choice restored after refresh |
| Wiring load | private development candidate saved as a 75-wire isolated practice draft |
| Wiring restore | 75 wires restored after page refresh and complete server restart |
| Board labels | PB0 NC; PB1/PB2 NO; F-1 through F-4 visible |
| Initial operation view | five scenario cards displayed `아직 확인하지 않음` |
| PB1 | X1 held after release; T1 reached 1000/1000ms; MC1, RL and M1 operated; WL changed from circuit state |
| STOP | X1/T1/MC1 dropped, T1 returned to 0/1000ms, no automatic restart |
| PB2 | X2 held; T2 reached 1000/1000ms; MC2, GL and M2 operated |
| EOCR | overload button enabled only with A1-A2 power and running motor; trip lit YL and stopped motor/timer; manual reset did not restart |
| Power | power-off reset coils/timer; restore did not restart |
| Fuse faults | each channel opened and recovered independently without changing the other channel |
| Full reset | power, timers, fuse states and scenario cards returned to initial state |
| Five scenarios | saved 75-wire draft showed five satisfied cards |
| Wire edit | deleting one wire autosaved 74; fresh operation session showed 3 satisfied and 2 unsatisfied with missing conditions |
| Restore | restoring 75 wires and reloading produced five satisfied cards again |
| Navigation | operation → wiring → operation kept the problem and used the latest saved wiring |
| Basic board | existing basic-board actual-wiring flow and four-terminal fuse rendered |
| Empty board | palette contained only `2회로 4단자 FUSE`, not a legacy two-terminal creation item |
| Other problem | Q-Net 011 remained unavailable and unchanged |
| Console | warning/error 0 |
| API responses/logs | private answer keys, candidate markers and private Net/test IDs 0 |

The UI continuously stated that it checks only behavior of the current wiring and does not provide answer comparison, a score, or pass/fail.
