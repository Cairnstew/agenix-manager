# Changelog

## [0.1.0] - 2026-06-05

### Added
- Import command for adding untracked `.age` files to manifest
- Automatic age binary detection; runs CI on PRs and tag pushes
- Secrets directory tracking and `.gitattributes` for `.age` files
- Confirmation modal to RemoveAction to guard against accidental deletions

### Fixed
- agenix binary resolution and `RULES` environment variable assignment
- TUI scope step no longer advances on Enter in SelectionList
- Replaced editor-based secret entry with in-TUI TextArea step
- Empty-table selection guards in RemoveScreen and TableScreen
- `AgenixOpError` raised when agenix/age binary not found; searches sudo user profiles
- Table now refreshes with updated config after removing a secret
- Missing `load_manifest` import in `context.py`; removed stale monolithic `cli.py`
- `agenixBin` was incorrectly set to the age binary instead of agenix, causing "missing recipients" errors

### Changed
- Fully keyboard-driven TUI wizard; removed button-based navigation
- Single status screen with ActionHandler hotkey dispatch
- Class-hierarchy architecture for CLI, TUI, and ops layers

### Docs
- Updated README, GOTCHAS, and STRUCTURE to reflect current architecture
