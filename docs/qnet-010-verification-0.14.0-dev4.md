# Q-Net 010 verification - private functional validation

## Evidence

- Official PDF: `전기기능사-010-A4, 2025-08-04.pdf`
- SHA-256: `e026b49d4e4e99595b0689ff2c890297dfc1f62d26a39db7b6e94263990f92ec`
- Reviewed pages: 6-9, rendered and visually inspected
- Supplement: user-provided field photo of the exam-practice FUSE holder

Evidence levels:

```text
structure_evidence:
- Q-Net PDF
- user-provided field photo

terminal_naming_evidence:
- user-provided practical convention

verification:
- unverified
```

The photo confirms one holder, left/right cartridges, and four physical connection points. PDF page 7 confirms two separate fuse paths. Neither source shows the digits 1-4. This implementation names the paths `1-2` and `3-4` as the user's practical convention only.

## Verification matrix

| Scope | Result | Notes |
| --- | --- | --- |
| PDF pages 6-9 | PASS | layout, sequence, required behavior, internal diagrams |
| FUSE one holder/two cartridges/four endpoints | PASS | PDF plus field photo |
| FUSE independent `1-2`, `3-4` implementation | PASS | convention implemented; no cross-channel intrinsic edge |
| Official FUSE physical terminal numbering | BLOCKED | no numbered photo or manufacturer/Q-Net diagram |
| X1/X2 8P | PASS | coil 2-7; groups 1/4/3 and 8/5/6 |
| T1/T2 8P | PASS | coil 2-7; two on-delay changeover groups |
| MC1/MC2 12P | PASS | main 1-7, 2-8, 3-9; NO 4-10; NC 5-11; coil 6-12 |
| EOCR 12P | PASS | L/U, L/V, L/W; NC 95-96; NO 97-98; A1-A2 |
| Complete private circuit | PASS | functional circuit, contacts, coils, terminals |
| Private expected Nets | PASS | 32 Nets, no TB number in expected signatures |
| 8P multiple answers | PASS | four whole-group alternatives, combinable |
| TB number independence | PASS | alternate TB numbers and wire trees accepted |
| Wrong/bypass validation | PASS | missing, short, merge, STOP/FUSE/EOCR/timer/MC/forced-coil |
| Actual-wiring operation | PASS | five deterministic private scenarios |
| Answer secrecy | PASS | public API/setup/session/source/bundle checks |
| Public availability | BLOCKED intentionally | draft/unverified evidence gate |

PDF 010 does not define a mutual MC1-MC2 interlock. No imaginary interlock was added. The MC auxiliary NC contacts are modeled as WL indication gates, and bypassing those contacts is rejected.

## Final decision

Functional implementation is present for private automated validation. Public grading and operation remain blocked until independent official/manufacturer evidence establishes the FUSE terminal numbering.
