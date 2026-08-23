# Handoff - Q-Net 010 private functional validation

## Repository state

- Branch: `feature/qnet-010`
- Base: `ca87754`, tag `v0.13.0-stable-fuse`
- Preserved documentation commit: `7a65a59`
- Q-Net 010 public status: `draft/unverified`
- Q-Net 001-009 and 011-018: untouched

## Implemented

- reproducible catalog-based Q-Net 010 JSON builder;
- complete functional circuit and actual-wiring operation definition;
- 32 private functional Nets;
- canonical wiring example without fixed TB signatures;
- X1/X2/T1/T2 whole changeover-group alternatives;
- Net candidate comparison in the existing grading path;
- package-validator alignment with runtime external/TB capacity rules;
- stable timer-contact reset recomputation;
- 34 dedicated tests and public privacy/blocking enforcement.

## Important design decisions

- FUSE `1-2`, `3-4` is a user-provided practical naming convention.
- The implementation remains unverified because official physical numbering is absent.
- No MC1-MC2 mutual interlock exists in PDF 010; none was invented.
- MC auxiliary NC contacts gate WL indication.
- General APIs suppress internal operation for unverified packages.
- Public wiring submissions remain ungradable and cannot create accepted snapshots or operation sessions.

## Test baseline

- Python: 185 passed
- Q-Net 010 dedicated: 34 passed
- Frontend: 67 passed
- Privacy focused: 49 passed
- Package validator: 0 errors
- Readiness: 19 PASS / 1 evidence BLOCKED
- Basic board, empty board, Q-Net 18, and Q-Net 010 smoke: PASS

## Remaining work

Obtain a manufacturer terminal diagram, Q-Net terminal-number document, or clear numbered field photo for the actual two-cartridge holder. Only then consider changing answer verification or public availability.

Do not migrate/delete SQLite data, drafts, accepted snapshots, workspaces, logs, or user records.
