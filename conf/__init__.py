import os
import yaml
from functools import cached_property
from pathlib import Path
from typing import (
    ClassVar, List, Optional, Dict,
    Type, TypeVar, Mapping, Any, Union
)

from pydantic import BaseModel, Field, validator

from .exceptions import ImproperlyConfigured


def get_env_name() -> str:
    if "ENV_NAME" in os.environ:
        return os.environ["ENV_NAME"]
    if "FLASKAPP_ENV" in os.environ:
        return os.environ["FLASKAPP_ENV"]
    return "dev"


ENV_NAME: str = get_env_name()


def _merge_dict(a: dict, b: dict, *others: dict):
    """
    merge dict a and b, return a new dict
    """
    dst = a.copy()
    for k, v in b.items():
        if k in dst and isinstance(dst[k], dict) and isinstance(b[k], Mapping):
            dst[k] = _merge_dict(dst[k], b[k])
        else:
            dst[k] = b[k]
    if others:
        return _merge_dict(dst, *others)
    else:
        return dst


def env_values(*, default: Any, **kwargs: Any) -> Any:
    """
    用于给 Settings 的 Field 设置按环境取值的默认值。用法举例: 

    class FooSettings(BaseConfig):
        bar: str = Field(default=env_values(
            dev="a",
            production="b",
            default="c",
        ))

    说明: 
    * 请总是提供 default 值, 如果没有合理的 default 值, 可在调用时传入 None 或 ..., 
      并在 validator 中处理该值。
    """
    if ENV_NAME in kwargs:
        return kwargs[ENV_NAME]
    return default


class BaseConfig(BaseModel):
    """
    各应用可以各自定义 config 模块, 所有 config 模块都继承此类。

    我们使用两个配置文件: main.config.yaml, config.yaml
        - main.config.yaml 保存项目配置（类似 settings.py 的功能）, 提交到 vcs。
        - config.yaml 保存环境配置（类似 settings_local.py 的功能）, 不提交到 vsc。

    main.config.yaml 和 config.yaml 中都允许为不同环境提供环境配置, 环境配置
    需要放在 `ENV_${env}` 键下面。

    注: config.yaml 本身就是环境配置, 理论上不需要再提供环境配置了。但是考虑有些
    开发者希望本地可以快速切换尝试不同的环境, 所以这里面允许提供环境值会带来便利。

    我们将首先读取 main.config.yaml, 后读取 config.yaml, 并合并数据。
    """

    # 在 config.yaml 中, 最顶层为 namespace, 所有配置都必须嵌套在某个 namespace 下
    config_namespace: ClassVar[str] = None  # type: ignore[assignment]

    _config_data: ClassVar[Dict] = None  # type: ignore[assignment]

    def __init__(self):
        if not self.__class__.config_namespace:
            raise ImproperlyConfigured(f"{self.__class__.__name__}.config_namespace not set.")

        if self.__class__._config_data is None:
            self.__class__._load_config_data()

        config_data = self.__class__._config_data.get(self.__class__.config_namespace, {})
        super().__init__(**config_data)


    @classmethod
    def _load_config_data(cls):
        project_config_data = cls._load_config_file(Path.cwd() / "main.config.yaml")
        local_config_data = cls._load_config_file(Path.cwd() / "config.yaml")
        cls._config_data = _merge_dict({}, project_config_data, local_config_data)

    @classmethod
    def _load_config_file(cls, file: Path) -> dict:
        if not file.exists():
            print(f"忽略不存在的配置文件: {file}")
            return {}

        try:
            with file.open(encoding="utf-8") as fp:
                data = yaml.safe_load(fp)
        except Exception:
            print(f"加载配置文件失败: {file}")
            raise

        env_keys = [key for key in data.keys() if key.startswith("ENV_")]
        env_overrides = {key[4:]: data.pop(key) for key in env_keys}
        env_data = env_overrides.get(ENV_NAME, {})

        data = _merge_dict(data, env_data)
        return data


ConfigType = TypeVar("ConfigType", bound=BaseConfig)


def lazy_init(ConfigClass: Type[ConfigType]) -> ConfigType:
    return SimpleLazyObject(lambda: ConfigClass())  # type: ignore[return-value,operator]


class LocalFsUploadAdapterConfig(BaseModel):
    """
    本地上传文件适配器配置

    TODO 建议推广使用 oss、废弃 LocalFsUploaderAdapter
    """

    root: Path = Field("data/upload/")
    base_url: str = Field("/upload/")


class Settings(BaseConfig):
    config_namespace: ClassVar[str] = "MpWechat"

    class Config:
        keep_untouched = (cached_property,)

    @property
    def ENV_NAME(self) -> str:
        """
        当前环境名称

        有5个保留值: `dev`、`review`、`testing`、`production`、`demo`, 
        分别对应本地开发环境、review、testing、生产环境, 以及（部分项目需要的）
        demo 环境。除这五个值以外, 也允许自定义其他值。

        该值只能通过环境变量 `ENV_NAME` 来设置, 默认为为 `dev`。
        """
        return ENV_NAME

    @cached_property
    def BASE_DIR(self) -> Path:
        """
        项目的根目录。

        我们默认为程序启动时的目录, 作为检查, 要求当前目录下存在 main.config.yaml
        文件, 否则报错。
        """
        cwd = Path.cwd()

        if not (cwd / "main.config.yaml").exists():
            raise RuntimeError("无法识别项目根目录, 请在根目录中启动进程, 根目录中要求存在 main.config.yaml 文件。")

        return cwd

    # Log config file
    LOG_CONFIG_FILE: Union[str, bool] = Field(None)

    @validator("LOG_CONFIG_FILE", always=True)
    def log_default_config(cls, v: Optional[str]) -> Union[bool, str]:
        """
        1. 如果没有配置LOG_CONFIG_FILE的值, 则进行最基本的日志配置
        2. 如果有值, 则先判断该文件的位置是否正确（是否在根目录下）
        3. 所有情况都符合, 则返回该文件的字符串, 供app初始化时设置
        """
        if v is None:
            print("未配置日志格式, 将使用默认格式")
            return False
        else:
            if not (Path.cwd() / v).exists():
                print(f"日志配置文件[{v}]不存在或者位置不正确, 请确保放在项目根目录下, 即requirements.txt的同级目录")
                return False
            else:
                return str(Path.cwd() / v)
    # DEBUG 模式。在 DEBUG 模式下, 会输出更多日志
    DEBUG: bool = Field(
        default_factory=lambda: env_values(
            production=False,
            demo=False,
            default=True,
        )
    )

    @validator("DEBUG", always=True)
    def debug_not_allowed_in_production_and_demo_env(cls, v: bool, values) -> bool:
        if ENV_NAME in ["production", "demo"] and v is True:
            raise ValueError(f"{ENV_NAME} 环境中禁止将 DEBUG 设置为 True")

        return v

    # 数据库 DEBUG 模式默认情况下与 DEBUG 同步, 但可单独设置
    DEBUG_DB: bool = Field(None)

    @validator("DEBUG_DB", always=True)
    def debug_db_default_to_debug(cls, v: Optional[bool], values) -> bool:
        if v is None:
            # v 值为 None, 表示初始化 Settings 时没有为 v 提供值
            return values["DEBUG"]
        return v

    # 一些场景, 如 password hasher、session、jwt 等需要使用 SECRET_KEY
    SECRET_KEY: str = Field(None)

    @validator("SECRET_KEY", always=True)
    def secret_key_must_be_set_in_nondebug_env(cls, v: str, values) -> str:
        if not values["DEBUG"] and v is ...:
            raise ValueError("在非 DEBUG 环境中必须配置 SECRET_KEY")

        if v is None:
            # 在 DEBUG 环境中, 如果未设置 SECRET_KEY, 我们默认设为 "SECRET"
            return "SECRET"

        return v

    # 安装的应用, 格式为:  "{module}.{AppConfigClass}"
    INSTALLED_APPS: List[str] = Field(default_factory=list)

    # 数据库配置
    DATABASE: str = Field(None)

    @validator("DATABASE", always=True)
    def validate_database_dsn(cls, v: Optional[str], values) -> str:
        if v is None:
            # 初始化时未提供 DATABASE 的值, 我们默认使用 sqlite
            print("[警告] 未设置 DATABASE, 默认使用:  sqlite://")
            return "sqlite://"

        """
        TODO 检查 DATABASE 的值是否是 sqlalchemy 支持的 dsn, 
        见: https://docs.sqlalchemy.org/en/13/core/engines.html

        取值样例: 
        * postgres: postgresql://{user}:{password}@{host}:{port}/{name}
        * mysql: mysql://{user}:{password}@{host}:{port}/{name}
        * sqlite (relative path): sqlite:///foo.db
        * sqlite (absolute path): sqlite:////path/to/foo.db
        * sqlite (:memory:): sqlite://
        """

        # 在 sqlalchemy 1.3 时, 支持 postgres://.. 的写法, 1.4 之后仅支持 postgresql://..
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql://")
        return v

    # 静态文件访问地址
    STATIC_URL: Optional[str] = None

    # 上传文件配置
    # TODO 应推广使用 oss, 尽快废弃 LocalFsUploadAdapter
    UPLOAD: LocalFsUploadAdapterConfig = Field(default_factory=LocalFsUploadAdapterConfig)


# 所有 App 的项目应当使用 settings = lazy_init(AppSettings), fastapp 的 settings 需要提前初始化, 
# 因此不使用 lazy_init。
settings: Settings = Settings()

__all__ = ["settings", "BaseConfig", "lazy_init", "env_values"]
