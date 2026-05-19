"""AI layer custom exceptions. Routers translate these to HTTP responses."""


class NoAPIKeyError(RuntimeError):
    """Raised when the chosen provider has no API key configured (neither in
    UserSettings nor as a fallback env var). Router returns 402."""

    def __init__(self, provider: str):
        self.provider = provider
        super().__init__(f"No {provider} API key configured")


class TokenBudgetExceededError(RuntimeError):
    """Raised when daily_token_budget is reached. Router returns 429."""

    def __init__(self, budget: int, used: int):
        self.budget = budget
        self.used = used
        super().__init__(f"Daily token budget exceeded: {used}/{budget}")
