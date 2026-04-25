# Archive Notes

This project was initialized from a spotDL source snapshot and then reshaped into
Xpotify Local Media Manager. The cleanup removed upstream maintenance and
distribution surfaces that no longer apply to this repository.

Removed before the first commit:

- `.github/`: upstream CI, issue templates, funding, stale, and PR templates.
- `.vscode/`: editor-local settings from the upstream project.
- `.readthedocs.yaml`: upstream ReadTheDocs publishing configuration.
- `Dockerfile`, `docker-compose.yml`, `.dockerignore`: upstream spotDL CLI
  container packaging.
- `scripts/`: upstream PyInstaller, zipapp, Termux, and MkDocs reference
  generation scripts.
- `docs/CODE_OF_CONDUCT.md`, `docs/CONTRIBUTING.md`: upstream community
  governance docs that should be replaced only if this project needs them.
- `docs/installation.md`, `docs/usage.md`, `docs/troubleshooting.md`: upstream
  user docs replaced by project-specific README and docs.
- `docs/images/`: upstream screenshots for the previous web UI.
- `.DS_Store`: generated macOS metadata.

Preserved:

- `LICENSE`
- `spotdl/`
- `tests/`
- `uv.lock`
- `pyproject.toml`, rewritten for Xpotify while keeping the `spotdl` CLI entry
  point for compatibility.

The original spotDL attribution is intentionally kept in `README.md`,
`docs/LEGAL_AND_USAGE.md`, and `LICENSE`.

