class LogicalError(Exception):
    """
    用于在 CRUD 代码中抛出业务逻辑错误

    我们将来需要严格解耦 view 代码与其他代码, 在非 view 代码中, 不应该抛出 Response Exception, 
    但许多时候确实有需要抛出简单的响应（只需要一行消息的）, 此时可以抛出 LogicalError。

    在 view 函数中, 如果可以接受此类错误, 则可以不用 catch, 全局 exception handler 会处理好。
    在 view 函数中也可以 catch 这些错误, 并自行处理。

    通常我们只需要附加 message 即可, 在必要时, 也可以抛出一个 code 字段, 便于 view 中进一步分析错误类型。
    """

    def __init__(self, message: str, code: int = None):
        self.message = message
        self.code = code
        super().__init__()

    def __str__(self):
        return self.message
