class ImproperlyConfigured(Exception):
    """
    用于所有跟配置错误相关的场景
    """

    def __init__(self, message: str):
        self.message = message
        super().__init__()

    def __str__(self):
        return self.message
