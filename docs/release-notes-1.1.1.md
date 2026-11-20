## What's fixed in 1.1.1

### "Scan from scanner" failed before reaching your scanner

Version 1.1.0 showed this error as soon as you pressed **Scan**:

> Windows did not answer the scanner. — *Missing expression after unary operator '--' … ParserError*

The scanner helper script was handed to PowerShell after `-Command`, and PowerShell
treats everything following `-Command` as *command text* — so the script could not receive
arguments, and a trailing `--` was parsed as code. WIA was never contacted; the scanner was
never asked to do anything.

**In 1.1.1 the script is written to a temporary `.ps1` and run with `-File`, which passes
arguments through `$args` as documented.** Both discovery and page acquisition now work.

### Two related faults fixed at the same time

- **Failures that are SmartScan's own are no longer blamed on your scanner.** A script
  error or a blocked PowerShell policy now says so explicitly — "This is a SmartScan
  problem, not a scanner problem — please report it" — instead of implying a loose cable.
- **The document feeder no longer aborts a healthy batch.** The feeder status probe is
  now best-effort; drivers that do not expose it simply keep scanning.

### Why this reached you

Every 1.1.0 test ran on Linux, where the scanner bridge is deliberately a no-op, so the
broken command line was never executed. The Windows build now runs the bridge for real:

- asserts the command line uses `-File` (never `-Command` with arguments),
- runs a PowerShell script for real and checks that arguments arrive in `$args`,
- calls device discovery and requires a parseable answer rather than a crash.

Seven new tests cover the same ground on any platform, including a replay of the 1.1.0
command that reproduces the exact error message you saw. 69 tests in total.

### Upgrading

Install over 1.1.0. Your settings are kept.
