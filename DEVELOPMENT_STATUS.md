# Development Status - Q-Net 010 contact labels and private wiring audit

## Current baseline

- Base tag: `v0.13.0-stable-fuse`
- Base commit: `ca87754f320be5c73d05bfb1dfaf6cc7cf5e3e7a`
- Branch: `feature/qnet-010`
- Program version policy: keep 0.13.0; this branch is not a verified release.

## Q-Net 010

The private development package now contains a functional circuit definition, 32 functional expected Nets, four independent 8P contact-group alternatives, and five actual-wiring operation scenarios.

Implemented internally:

- one FUSE holder, two cartridges, four terminals;
- implementation convention `1-2` and `3-4`, with no cross-channel intrinsic connection;
- MCCB, EOCR, X1, X2, T1, T2, MC1, MC2, buttons, limit switches, lamps, and two motors;
- PDF page 9 mappings for 8P relay/timer and 12P MC/EOCR;
- TB5/TB6-number-independent Net comparison;
- whole COM/NC/NO group swaps for X1, X2, T1, and T2;
- missing, wrong, shorted, merged, bypassed, isolated-jumper, and capacity-error validation;
- actual submitted-wiring operation validation for PB1/PB2, timers, motors, STOP, EOCR, indicators, and reset;
- stable-state recomputation when a completed timer de-energizes.

Implemented in the public UI without exposing answer data:

- metadata-driven `NO`/`NC` text badges beside push-button and limit-switch names;
- Q-Net 010 metadata: PB0 `NC`, PB1/PB2 `NO`, LS1/LS2 `NO`;
- the same badge component on wiring and operation screens;
- terminal numbers remain separately visible and selectable;
- missing contact metadata falls back safely without guessing.

## User candidate audit

The supplied 62-line wiring answer is preserved and reviewed only in private test/document paths. It matches 21 of 32 production Nets directly and 31 of 32 under an audit-only dry-contact endpoint projection. Its direct wiring passes all five private operation scenarios, so the sequence intent is substantially correct. It is nevertheless classified as `기능 Net 후보이나 완성 실기결선으로는 오답` because PE is absent and omitted TB distribution produces seven terminal-capacity overflows. Production grading was not relaxed and no answer alternative was added.

## Public state

Q-Net 010 remains:

- manifest: `draft`
- answer verification: `unverified`
- public wiring grading: blocked
- public operation setup/session: blocked
- private answer/API/bundle/log exposure: blocked

The field photo confirms one holder with two physically separate cartridges and four connection points. The PDF confirms two independent fuse paths. The labels `1-2` and `3-4` are a user-provided practical convention, not a Q-Net or manufacturer terminal-number claim.

## Readiness

- Functional readiness: 19 PASS
- Evidence gate: 1 BLOCKED
- Remaining BLOCKED: no Q-Net/manufacturer document or numbered field photo establishes the official physical numbering of the four FUSE terminals.

Q-Net 001-009 and 011-018 were not implemented or changed.
