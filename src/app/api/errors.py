class SentinelAPIError(Exception):
    """Base exception for controlled SentinelAI API failures."""

    status_code: int = 500
    error_code: str = "internal_error"
    public_message: str = "SentinelAI could not complete the request."

    def __init__(
        self,
        *,
        thread_id: str | None = None,
        trace_id: str | None = None,
    ) -> None:
        super().__init__(self.public_message)
        self.thread_id = thread_id
        self.trace_id = trace_id


class RuntimeUnavailableError(SentinelAPIError):
    """Raised when the application runtime is unavailable."""

    status_code = 503
    error_code = "runtime_unavailable"
    public_message = "SentinelAI runtime is temporarily unavailable."


class WorkflowExecutionError(SentinelAPIError):
    """Raised when the multi-agent workflow fails during execution."""

    status_code = 500
    error_code = "workflow_failed"
    public_message = "SentinelAI workflow could not be completed."


class WorkflowIncompleteError(SentinelAPIError):
    """Raised when the workflow finishes without a usable answer."""

    status_code = 500
    error_code = "workflow_incomplete"
    public_message = "SentinelAI workflow completed without a final answer."