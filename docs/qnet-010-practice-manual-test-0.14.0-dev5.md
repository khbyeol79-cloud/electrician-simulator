# Q-Net 010 ungraded practice mode - manual browser check

Date: 2026-08-24
Server: production `frontend/dist` through FastAPI at `http://127.0.0.1:8765`

## Executed and passed

1. Selected Q-Net public problem 010 from the 18-problem chooser.
2. Opened the wiring stage despite `draft/unverified`.
3. Confirmed the persistent text banner says ungraded practice and disclaims answers/pass/fail.
4. Confirmed the board contains one F item with selectable F-1, F-2, F-3, and F-4 terminals; the existing renderer shows two cartridges.
5. Confirmed PB0 has a textual NC badge; PB1/PB2 and LS1/LS2 have textual NO badges.
6. Confirmed external terminal 1/2 labels and board terminal buttons remain selectable.
7. Created the deliberately invalid F-1 to F-3 wire by terminal clicks.
8. The first attempt exposed an existing router crash for an unroutable wrong wire. The router was fixed to use a visible orthogonal fallback, rebuilt, and the same interaction then stayed on the wiring page without console error.
9. Saved and opened the practice operation screen.
10. Confirmed the operation screen persists the ungraded-practice banner and says the source is the user practice draft.
11. Confirmed actual-wiring/catalog calculation and controls for PB0/PB1/PB2/LS1/LS2, coils, timers, lamps, motors, EOCR, and reset are present.
12. Confirmed FUSE channel merge is reported in words, the power button is disabled, and no automatic operation-check button, score, correctness, pass, or fail result is shown.

## Not manually executed

- Drag gesture (click wiring was executed; drag remains covered by existing frontend interaction tests).
- Browser restart/server restart restoration (SQLite repository persistence and restart-compatible storage are automated).
- A complete safe 60+ wire user solution and every PB/LS/timer/relay/MC/lamp/motor sequence.
- Safe-wire correction followed by power-on.
- EOCR trip/manual reset through this exact Q-Net 010 browser session.
- Manual visits to all other 17 Q-Net blocked pages, basic board, and empty board in the browser.

These items are recorded as `미실행`, not manual passes. The common engine sequences, safety state, other official-draft capability blocks, user isolation, basic board, empty board, and Q-Net 18 loading are covered by automated tests/smoke commands.

## Result

The implemented browser path supports ungraded Q-Net 010 editing and an actual-wiring preview while visibly separating safety from answer grading. The evidence state remains `draft/unverified`; F-1/F-2/F-3/F-4 are implementation-convention names, not asserted official Q-Net terminal numbers.
