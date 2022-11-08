import time
from typing import Dict, Generic, List, Literal, Optional, TypeVar

from pydantic import BaseModel, Field
from pydantic.generics import GenericModel


class APIResponseModel(BaseModel):
    pass


class OkResponseModel(APIResponseModel):
    """
    用于 200 Ok 的响应

    200 响应的 body 常见有三种情况：

    * 空对象：`{}`
    * 只包含一个 message 字段：`{"message": "..."}`
    * 需要返回的内容 data

    由于格式不确定，因此在构造 Response 的地方进行处理。
    """

    pass


class Pagination(BaseModel):
    # 条目总数
    total: int
    # 当前页码（页码从1开始）
    page: int
    # 每页条目数量
    page_size: int
    # 最后一页的页码
    last_page: int


PageItemModel = TypeVar("PageItemModel")


class PageResponseModel(GenericModel, Generic[PageItemModel]):
    data: List[PageItemModel]
    pagination: Pagination

    # 以下字段兼容 Ant Design 的表格
    total: int
    success: bool = True


class BadRequestResponseModel(APIResponseModel):
    """
    用于 400 Bad Request 的响应

    该类型一般用于简单的业务逻辑错误，只需要一个 message 即可。
    """

    message: str


class BizErrorResponseModel(APIResponseModel):
    """
    用于 400 Bad Request 的响应

    该类型一般用于复杂的业务逻辑错误，需要携带一个 code
    """

    code: int
    message: str


class NotAuthorizedResponseModel(APIResponseModel):
    """
    用于 401 Not Authorized 的响应
    """

    message: str = "请登录后访问"


class ForbiddenResponseModel(APIResponseModel):
    """
    用于 403 Forbidden 的响应
    """

    message: str = "无权限访问"


class NotFoundResponseModel(APIResponseModel):
    """
    用于 404 Not Found 的响应
    """

    message: str = "资源不存在"


class NotImplementedResponseModel(APIResponseModel):
    """
    用于 501 Not Implemented 的响应
    """

    message: str = "该接口尚未实现"


class Client(BaseModel):
    """
    X-NS-Client

    X-NS-Client 一般格式为 "{name}/{version}"，也可以省略 version，为 "{name}"
    """

    name: str = Field(title="客户端名称")
    version: Optional[str] = Field(None, title="客户端版本")

    @classmethod
    def parse_header(cls, header: Optional[str]) -> Optional["Client"]:
        if not header:
            return None

        if "/" not in header:
            return cls(name=header, version=None)

        name, version = header.split("/", 1)
        return cls(name=name, version=version)


class Token(BaseModel):
    """
    Token 基础模型
    """

    subject_type: Literal["user", "app", "anonymous"] = Field(title="授权主体类型", description="支持 `user`, `app`")
    subject_id: str = Field(title="授权主体 ID", description="具体值的含义，由签发者定义")
    audience: str = Field(title="Token 听众")
    expires: Optional[int] = Field(title="Token 有效期", description="该值为 Unix 时间戳，None 表示长期有效")
    scopes: Optional[List[str]] = Field(title="Token 授权内容")
    payload: Dict = Field(default_factory=dict, title="额外的数据")

    tenant: Optional[str] = Field(description="该值仅在 SaaS 中使用，表示平台租户，值为 Tenant.uid")

    token: str = Field(title="唯一标识，可用于给用户")

    def is_expired(self):
        return self.expires < time.time()

    @property
    def valid_seconds(self) -> Optional[int]:
        if self.expires is None:
            return None
        return int(time.time()) - self.expires

    def has_scope(self, scope: str) -> bool:
        return self.scopes is None or scope in self.scopes

    def has_perm(self, perm: str) -> bool:
        if self.subject_type == "app":
            # app 的 Token 总是没有 perm 权限
            return False

        return "perms" in self.payload and perm in self.payload["perms"]
