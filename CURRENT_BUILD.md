# Current Recommended Build

**Build:** 0.13.0 stable-fuse base with Q-Net 010 contact labels and private wiring audit

This feature branch keeps the existing 0.13.0 version policy. It is not a verified public Q-Net 010 release.

## Added on feature/qnet-010

- complete private Q-Net 010 circuit, terminals, contacts, coils, and operation definition;
- FUSE one-holder/two-cartridge/four-terminal structure;
- practical-convention FUSE paths `1-2` and `3-4`;
- 32 private expected Nets;
- TB-number-independent and alternate-wire-tree grading;
- X1/X2/T1/T2 whole contact-group alternatives;
- actual submitted-wiring operation validation;
- wrong, shorted, merged, bypassed, and capacity-error tests;
- public answer and operation suppression for unverified official packages.
- metadata-driven `NO`/`NC` text badges on wiring and operation screens;
- private 62-line candidate audit with production grading unchanged.

## Public behavior unchanged

Q-Net 010 remains `draft/unverified`. Public wiring grading and operation stay blocked. Q-Net 001-009 and 011-018 are unchanged.

The user candidate passes the five operation scenarios but remains unsuitable as a complete practical submission because PE is missing and direct device fan-out exceeds seven terminal capacities. It is retained only in private audit/test artifacts and is absent from public API data and the frontend bundle.

## Evidence gate

The PDF and field photo confirm structure, but not official physical terminal digits. `1-2`, `3-4` is an implementation convention supplied by the user and is not represented as a Q-Net or manufacturer numbering claim.
