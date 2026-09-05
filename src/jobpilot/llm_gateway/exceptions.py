class GatewayError(Exception):
    """网关层错误基类."""


class GatewaySchemaError(GatewayError):
    """多次重试后仍未产出符合 schema 的输出."""

    def __init__(self, message: str, last_error: Exception | None = None):
        super().__init__(message)
        self.last_error = last_error


class BudgetExceeded(GatewayError):
    """当月 API 费用超出预算,网关拒绝继续调用."""
