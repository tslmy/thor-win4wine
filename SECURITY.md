# Security and privacy

- The public repository contains source, recipes and text notes only. Runtime
  binaries, source/build caches, screenshots, Windows/ReactOS media, prefixes,
  local `.env` files and SSH private keys are excluded.
- `just audit` checks tracked source for common credential patterns and binary/media
  payloads. It is a heuristic, not a guarantee; full-history Gitleaks scanning is
  also used before the initial publication. Never paste secrets into an issue.
- Public historical snapshots have local paths, private device addresses and
  personal author/committer identity redacted. A GitHub repository's owner is
  necessarily public; anonymized commits do not hide who hosts the repository.
- No Windows activation/product key, password, token or SSH private key is needed
  by these recipes. Use your existing SSH agent/config and verify host keys.
- Windows XP/7 and their legacy browsers are obsolete. Do not use the legacy
  shell components to browse untrusted sites, and do not expose Wine services
  or SSH to an untrusted network without your normal security controls.
- Root registration and switching scripts are powerful. Review them first.
  Keep the stock Armada sessions and SSH recovery available. Do not run upstream
  `scripts/setup.sh` on Armada: it may install system packages/change display managers.
- Container builds download third-party source/packages. Run only trusted recipes
  and locally built deployment archives. Source pins do not remove upstream risk.

For a suspected leaked credential: do not repeat it publicly. Revoke/rotate it
first and contact the repository owner privately through GitHub's available
security-reporting/contact mechanisms. Display failures may require device logs;
redact identifiers and keep screenshots out of public reports unless intentional.
