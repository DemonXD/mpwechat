from pathlib import Path
from typing import Any, ClassVar, Dict, List, Mapping, Type, TypeVar, Union

import yaml
from pydantic import BaseModel

from fastframe.core.exceptions import ImproperlyConfigured
from fastframe.utils.appenv import ENV_NAME
from fastframe.utils.functional import SimpleLazyObject


def _merge_dict(a: dict, b: dict, *others: dict) -> dict:
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
    用于给 Settings 的 Field 设置按环境取值的默认值。用法举例：

    class FooSettings(BaseConfig):
        bar: str = Field(default=env_values(
            dev="a",
            production="b",
            default="c",
        ))

    说明：
    * 请总是提供 default 值，如果没有合理的 default 值，可在调用时传入 None 或 ...，
      并在 validator 中处理该值。
    """
    if ENV_NAME in kwargs:
        return kwargs[ENV_NAME]
    return default


class BaseConfig(BaseModel):
    """
    各应用可以各自定义 config 模块，所有 config 模块都继承此类。

    我们使用两个配置文件：project.config.yaml, config.yaml，其中，
    project.config.yaml 保存项目配置（类似 settings.py 的功能），提交到 repo。
    config.yaml 保存环境配置（类似 settings_local.py 的功能），不提交到 repo。

    project.config.yaml 和 config.yaml 中都允许为不同环境提供环境配置，环境配置
    需要放在 `ENV_${env}` 键下面。

    注：config.yaml 本身就是环境配置，理论上不需要再提供环境配置了。但是考虑有些
    开发者希望本地可以快速切换尝试不同的环境，所以这里面允许提供环境值会带来便利。

    我们将首先读取 project.config.yaml，后读取 config.yaml，并合并数据。
    """

    # 在 config.yaml 中，最顶层为 namespace，所有配置都必须嵌套在某个 namespace 下
    config_namespace: ClassVar[Union[str, List[str]]] = None  # type: ignore[assignment]

    _config_data: ClassVar[Dict] = None  # type: ignore[assignment]

    def __init__(self):
        if not self.__class__.config_namespace:
            raise ImproperlyConfigured(f"{self.__class__.__name__}.config_namespace not set.")

        if self.__class__._config_data is None:
            self.__class__._load_config_data()

        config_data = self._get_namespaced_data(self.__class__._config_data, self.__class__.config_namespace)
        super().__init__(**config_data)

    @classmethod
    def _get_namespaced_data(
        cls: Type["BaseConfig"], root: dict, namespace: Union[str, List[str]]
    ) -> Union[dict, Type["BaseConfig"]]:
        if isinstance(namespace, str):
            return root.get(namespace, {})
        elif isinstance(namespace, list):
            if len(namespace) == 0:
                return root
            return cls._get_namespaced_data(root.get(namespace[0], {}), namespace[1:])
        else:
            raise RuntimeError(f"{cls.__name__}.config_namespace must be str or list of str")

    @classmethod
    def _load_config_data(cls):
        project_config_data = cls._load_config_file(Path.cwd() / "project.config.yaml")
        local_config_data = cls._load_config_file(Path.cwd() / "config.yaml")
        cls._config_data = _merge_dict({}, project_config_data, local_config_data)

    @classmethod
    def _load_config_file(cls, file: Path) -> dict:
        if not file.exists():
            print(f"忽略不存在的配置文件：{file}")
            return {}

        try:
            with file.open(encoding="utf-8") as fp:
                data = yaml.safe_load(fp)
        except Exception:
            print(f"加载配置文件失败：{file}")
            raise

        env_keys = [key for key in data.keys() if key.startswith("ENV_")]
        env_overrides = {key[4:]: data.pop(key) for key in env_keys}
        env_data = env_overrides.get(ENV_NAME, {})

        data = _merge_dict(data, env_data)
        return data


ConfigType = TypeVar("ConfigType", bound=BaseConfig)


def lazy_init(ConfigClass: Type[ConfigType]) -> ConfigType:
    return SimpleLazyObject(lambda: ConfigClass())  # type: ignore[return-value,operator]
