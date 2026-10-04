# Storage & Drive Policy

## CRITICAL RULE: F: Drive Only
All data, code, files, dependencies, libraries, virtual environments, caches, datasets, and temporary files associated with this project MUST remain strictly on the **`F:` drive** (specifically inside `F:\job wala project\` or subdirectories within `F:`).

### Strict Guidelines:
1. **No Data on C:, D:, or E: Drives**:
   - Never install packages globally onto the `C:` drive.
   - Python virtual environments must always be created inside the project folder (e.g., `F:\job wala project\.venv`).
   - Node/npm dependencies must be kept in `F:\job wala project\node_modules`.
   - Node / npm / pip / HuggingFace / PyTorch cache directories must be pointed to `F:\job wala project\.cache` or equivalent paths on `F:`.
2. **Environment & Cache Overrides**:
   - If a package manager, script, or tool defaults to saving data in `C:\Users\Admin\...` or `AppData` / `Temp`, explicitly configure environment variables (e.g., `PIP_CACHE_DIR`, `npm_config_cache`, `HF_HOME`, `TMPDIR`, etc.) to point inside `F:\job wala project\.cache` or `F:\job wala project\tmp`.
3. **Handling Spillover / Relocation**:
   - If any tool, dependency, or file inadvertently generates output on `C:`, `D:`, or `E:`, immediately relocate it to `F:\job wala project\`, update configuration/environment pointers, and ensure the process continues seamlessly without broken references.

## Context Tracking Rule: context.md
- **Mandatory Per-Iteration Updates**: With **EACH iteration** of work (regardless of size—whether code changes, schema migrations, dependency installations, audits, refactoring, bug fixes, or test executions), whatever was done MUST be immediately recorded in `F:\job wala project\context.md` before concluding the response or turn.
- **No Deferred Logging**: Never defer logging to future steps. Updates must occur in real-time as work happens to preserve complete, unbroken continuity across turns and sessions.
- **Evidence Required**: Every entry must include concrete evidence (exact file paths modified, commands run, execution outputs, migration revision IDs, and architectural reasoning) so that context remains rich, continuous, and verified.


