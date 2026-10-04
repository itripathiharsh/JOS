# Rule: Mandatory Per-Iteration Context Tracking in context.md

## CRITICAL RULE: Update context.md On Every Iteration
With **each and every iteration** of work (regardless of size—whether code modifications, database migrations, dependency installations, audits, refactoring, bug fixes, or test executions), whatever was done MUST be immediately recorded in `F:\job wala project\context.md` before concluding the response or turn.

### Strict Guidelines:
1. **Never Defer Logging**:
   - Updates to `context.md` must not be batched or deferred to subsequent turns or future milestones.
   - Every completed task, audit step, or code change must be committed to `context.md` during the active iteration in which it was executed.
2. **Evidence & Verification Required**:
   - Every entry in `context.md` must document:
     - **Iteration Objective**: What was requested or addressed in this turn.
     - **Actions Taken**: Clear breakdown of modifications made.
     - **Exact Files & Symbols**: Clickable file paths (`file:///F:/job%20wala%20project/...`) and symbol references.
     - **Commands & Execution Evidence**: Commands executed and terminal/test outputs confirming success or status.
     - **Architectural / Design Decisions**: Rationale for schemas, constraints, and fixes.
     - **Current State & Next Steps**: State of database, services, build integrity, and explicit pending items.
3. **Continuous Source of Truth**:
   - `context.md` serves as the persistent cross-session memory for the project. An iteration is not considered complete until `context.md` reflects the work done.
