# Opt-in local checks

Follow README Offline checks. Prepare Python 3.12+, cached Go **1.27.1**, the local pinned engine Git object, cached Go dependencies and the existing isolated .baseline-work/source snapshot explicitly. Hook does not create a snapshot or fetch the engine.

## Installation and push contract

Enable explicitly with `bash scripts/install-hooks.sh` using Bash/Git Bash. Windows-target repositories also provide `pwsh -NoProfile -File scripts/install-hooks.ps1`. Installer is idempotent and refuses to hide existing active hooks or replace custom core.hooksPath. Relative repository-local .githooks resolves within each linked worktree. It is never installed automatically.

Every nondeleted ref must resolve to checked-out HEAD. Checks require a clean checkout including nonignored untracked files. No stash, rewriting, fetch or actual push occurs. New refs, unavailable bases, empty input/ranges, deletions, renames and shared changes broaden to full project checks. Multiple refs are consumed before one validation. Deleted refs alone skip. Other commits need their own clean checkout.

## Commands and acceptance

`python3 scripts/baseline/baseline.py validate --engine ../hermes`, then Python unittest discovery in scripts/baseline. Existing validator verifies pinned snapshot bytes and inventory. GOPROXY=off, GOSUMDB=off and GOTOOLCHAIN=local prevent module/toolchain downloads. Never runs inventory, record, crawling or publishing.

Pinned engine object, Go 1.27.1, snapshot validation and Python tests passed in secret-free Boat. Local users must prepare those prerequisites explicitly. Frozen fixture/golden data remain unchanged. No fresh-site qualification.

`python3 scripts/hooks/test-hooks.py` exercises executable hooks and installers in disposable Git repositories with stub project commands, including linked worktrees. No actual push. Harness evidence is separate from actual project/native acceptance. No under-nine-second promise, CI activation or affected-only optimization is claimed. No user hooks were installed during preparation.
