External EOD sector screen trigger.

Created 2026-09-04 to remove the manual GitHub Actions dispatch step from the first sector-first evidence run. The workflow remains credential-gated by the repository Actions secret TIINGO_TOKEN and will fail before external requests if the secret is absent.
