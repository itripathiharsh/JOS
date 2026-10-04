# Rule: Strict F Drive Storage Only

- **Workspace Path**: `F:\job wala project`
- **Scope**: All code, assets, datasets, packages, virtual environments, caches (`.venv`, `node_modules`, pip cache, npm cache, models, temp files) must reside strictly on `F:` drive.
- **Prohibited Drives**: Do not store project data on `C:`, `D:`, or `E:`.
- **Cache Direction**: When executing installs or scripts, route caches and temp folders to `F:\job wala project\.cache` or `F:\job wala project\tmp` rather than `%USERPROFILE%` or `%TEMP%` on C:.
- **Recovery & Relocation**: If anything writes to C: or another drive, relocate it to `F:\job wala project`, create required directories, and patch configuration/paths so executions are not interrupted.
