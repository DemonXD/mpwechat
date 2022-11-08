import os


# 统一使用 ENV_NAME 来表示当前的环境，
# 允许的取值如：dev、testing、review、production、demo 等等
def get_env_name() -> str:
    if "ENV_NAME" in os.environ:
        return os.environ["ENV_NAME"]
    if "FLASKAPP_ENV" in os.environ:
        return os.environ["FLASKAPP_ENV"]
    return "dev"


ENV_NAME: str = get_env_name()
FLASKAPP_ENV: str = get_env_name()


def is_fastapp() -> bool:
    # NOTE: 在 FlaskAPP 启动脚本中设置该变量，因此在设置之前，读取该值会返回 False
    return "IS_FLASKAPP" in os.environ


def set_is_fastapp():
    os.environ["IS_FLASKAPP"] = "true"
