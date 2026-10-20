# GramSeva Developer & Agent Rules

## 1. Core Mandates
1. **Zero UI / Theme Regressions**: Never alter CSS design tokens, typography, glassmorphism card styling, color variables, or HTML template structures without explicit user instruction.
2. **Workflow Invariants**: The 6-stage lifecycle (`SUBMITTED` -> `UNDER_REVIEW` -> `ASSIGNED` -> `IN_PROGRESS` -> `WORK_COMPLETED` -> `OFFICER_VERIFICATION` -> `CITIZEN_VERIFICATION` -> `VERIFIED` -> `RESOLVED` -> `CLOSED`) is strictly enforced at the backend service layer.
3. **Role-Based Separation of Duties**:
   - `citizen`: Can only register complaints, view own complaints, rate resolved complaints, and verify issue status.
   - `worker`: Can view assigned tasks, update progress, and submit completion proofs. Strictly forbidden from marking tickets as `RESOLVED` or `CLOSED`.
   - `officer`: Can verify physical completion proofs, review department tickets, and trigger telephony verification calls.
   - `admin`: Full supervisory access across departments, assignments, announcements, and global metrics.
4. **Data Privacy**: Citizen phone numbers and full names must remain masked for unauthorized or guest visitors.
5. **No Cloned External Repositories**: Do not clone large external repositories into local project storage. Extract architectural patterns, skills, and prompts into local modular components.
