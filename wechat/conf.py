from typing import Optional, ClassVar
from conf import BaseConfig, lazy_init
from pydantic import BaseModel, Field


class LocalSettings(BaseModel):
    bind_service_token: Optional[str] = None

class WechatConfig(BaseConfig):
    config_namespace: ClassVar[str] = "wechat"
    local: LocalSettings = Field(default_factory=LocalSettings)

settings = lazy_init(WechatConfig)
