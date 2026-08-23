# Q-Net 010 manual check - private functional validation

## Public UI checks

1. Open Q-Net public problem 010.
2. Confirm its state remains draft/unverified.
3. Confirm the page-7 schematic can be inspected.
4. Confirm one FUSE body shows two cartridges and four endpoints.
5. Confirm no public response contains expected Nets, alternatives, wiring examples, or operation tests.
6. Submit any wiring and confirm the result is ungradable.
7. Open operation setup and confirm the evidence-pending message appears.
8. Confirm operation preview/session creation is unavailable.

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
