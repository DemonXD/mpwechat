from typing import Any, List, Optional, Type, Union, overload
from flask import Request

from sqlalchemy.orm import Query

from core.schemas.api.v1 import (
    APIResponseModel,
    BadRequestResponseModel,
    BizErrorResponseModel,
    ForbiddenResponseModel,
    NotAuthorizedResponseModel,
    NotFoundResponseModel,
    NotImplementedResponseModel,
    OkResponseModel,
    PageResponseModel,
)
from db import Model, SmartQuery
from responses.pagination import get_pagination
from utils.convert import convert

class PaginationParams:
    def __init__(self, request: Request):
        self.page = request.args.get("page") or request.args.get("current") or 1
        self.page_size = request.args.get("page_size") or request.args.get("pageSize") or 10


class APIResponse:
    status_code: int = 200
    response_model: Optional[Type[Any]] = APIResponseModel

    def __init__(self, **kwargs):
        self.content = self.render_content(**kwargs)

    def render_content(self, **kwargs):
        if not self.response_model:
            if "content" not in kwargs:
                raise RuntimeError(f"{self.__class__.__name__}: 未指定response_model, 必须提供content参数")
            return (dict(kwargs["content"]), self.status_code)
        # 这里在实际使用Model和BaseModel的时候可能会报错, 持续关注
        return (dict(convert(self.response_model, kwargs, self.__class__.__name__)), self.status_code)


class Ok(APIResponse):
    """
    可以返回空, message, 和单个model的数据
    """

    status_code = 200
    response_model: Optional[Type[Any]] = OkResponseModel

    @overload
    def __init__(self):
        ...

    @overload
    def __init__(self, *, response_model: Type[Any], data: Any):
        ...

    @overload
    def __init__(self, *, data: Any):
        ...

    def __init__(
        self,
        *,
        response_model: Type[Any] = None,
        data: Any = ...,
        message: Optional[str] = None,
    ):
        if response_model is not None:
            if data is ...:
                raise ValueError(f"{self.__class__.__name__}: 提供 response_model 时, 必须提供 data")
            # 将 response_model 设置为 None, 从而 APIResponse 中不再做序列化
            self.response_model = None
            content = convert(response_model, data)
            super().__init__(content=content)
        elif message is not None:
            self.response_model = None
            content = dict(message=message)
            super().__init__(content=content)
        elif data is not ...:
            self.response_model = None
            super().__init__(content=data)
        else:
            super().__init__(content={})


class Full(APIResponse):
    """
    不做分页处理的数据
    """

    status_code = 200
    response_model = None

    @overload
    def __init__(self):
        ...

    @overload
    def __init__(self, *, response_model: Type[Any], datas: List[Any] = []):
        ...

    def __init__(self, *, response_model: Type[Any] = None, datas: List[Model] = None):
        if response_model is not None:
            if datas is []:
                raise ValueError(f"{self.__class__.__name__}: 提供 response_model 时, 必须提供 data")


class Page(APIResponse):
    """
    TODO：需要完善
    """

    status_code = 200
    response_model = None

    @overload
    def __init__(self, item_model: Type[Any], *, query: Union[Query, Any], page_params: PaginationParams):
        ...

    @overload
    def __init__(self, item_model: Type[Any], *, items: List[Model], pagination: dict):
        ...

    def __init__(self, item_model, *, query=None, page_params=None, items=None, pagination=None):
        self.response_model = PageResponseModel[item_model]
        if query is not None:
            if isinstance(query, SmartQuery):
                query = query.query
            items, pagination = get_pagination(query, page=page_params.page, page_size=page_params.page_size)
        super().__init__(data=items, pagination=pagination, total=pagination["total"])


class BadRequest(APIResponse):
    status_code = 400
    response_model = BadRequestResponseModel


class BizError(APIResponse):
    status_code = 400
    response_model = BizErrorResponseModel


class NotAuthorized(APIResponse):
    status_code = 401
    response_model = NotAuthorizedResponseModel


class Forbidden(APIResponse):
    status_code = 403
    response_model = ForbiddenResponseModel


class NotFound(APIResponse):
    status_code = 404
    response_model = NotFoundResponseModel


class NotImplemented(APIResponse):
    status_code = 501
    response_model = NotImplementedResponseModel
