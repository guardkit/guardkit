Next Sprint -- Medium Priority
TASK-CRV-9914 (Extended CoachValidator): Dependencies (CRV-412F, CRV-537E) are now met. This architectural refactor moves runtime verification from orchestrator into Coach, enabling a cleaner feedback loop for failed commands.

TASK-CRV-3B1A (SDK session resume): Would eliminate CancelledError entirely by enabling Player session resumption. Dependency (CRV-1540) is met.

Deprioritise
TASK-CRV-B275 (Rate limit detection): No rate limit errors observed. Defensive improvement only.
TASK-CRV-7DBC (MCP Coach integration): Depends on CRV-9914 which isn't started. Long dependency chain