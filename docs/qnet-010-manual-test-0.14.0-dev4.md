# Q-Net 010 manual check - private functional validation

## Public UI checks

1. Open a verified demo with push-button metadata and confirm a visible text badge appears beside each device name: PB0 `NC`, PB1 `NO`, and LS1 `NO`.
2. Confirm the same labels appear on the operation screen.
3. Confirm terminal numbers such as PB0-1 and PB0-2 remain visible and selectable.
4. Activate a push button and confirm operation still responds.
5. Open Q-Net public problem 010 and confirm its state remains draft/unverified.
6. Confirm the page-7 schematic can be inspected.
7. Confirm one FUSE body shows two cartridges and four endpoints.
8. Confirm no public response contains expected Nets, alternatives, wiring examples, operation tests, or the supplied 62-line candidate.
9. Submit any wiring and confirm the result is ungradable.
10. Open operation setup and confirm the evidence-pending message appears and session creation is unavailable.

## Manual result on 2026-08-24

- Wiring screen: PB0 `NC`, PB1 `NO`, LS1 `NO` visible; no overlap observed.
- Terminal interaction: PB0-1 selected successfully while the badge remained visible.
- Operation screen: the same badges were visible and PB1 control worked.
- Browser console: zero errors.
- Data isolation: the check used a temporary data directory; no existing SQLite database was opened or changed.

## Internal automated checks

The private test suite validates:

- canonical wiring and alternate TB numbering;
- alternate wire trees within the same Net;
- X1/X2/T1/T2 whole changeover-group swaps;
- partial or semantically invalid pin swaps rejected;
- missing wires, wrong terminals, shorts, separated-Net merges;
- STOP, FUSE, EOCR, timer, MC, auxiliary-contact, and forced-coil bypasses;
- isolated TB jumpers and terminal-capacity overflow;
- PB1-X1-LS1-T1-MC1-M1/RL;
- PB2-X2-LS2-T2-MC2-M2/GL;
- WL transition, EOCR trip/YL, manual reset, STOP, and power reset;
- repeated operation tests without prior-state leakage.

## Expected public result

The board and source schematic remain viewable. Grading and operation remain blocked. The implementation convention `1-2`, `3-4` must never be described as official Q-Net/manufacturer numbering.
