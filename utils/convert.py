from typing import Any, Dict, Type, TypeVar

from pydantic import BaseConfig, BaseModel, ValidationError, create_model
from pydantic.fields import ModelField

InputType = TypeVar("InputType")

_cached_fields: Dict[Type[Any], ModelField] = {}


class ValidationErrorWrap(ValidationError):
    # pydantic.ValidationError() 期望第二个参数是一个 BaseModel 的子类，
    # 我们的 model 可能并不是 BaseModel（如 int, Union[int, str] 等），
    # 因此这里封装一下。
    Model: Type[BaseModel] = create_model("convert()")

    def __init__(self, errors, model):
        try:
            if issubclass(model, BaseModel):
                super().__init__(errors, model)
            else:
                super().__init__(errors, self.__class__.Model)
        except TypeError:
            super().__init__(errors, model)


def create_model_field(model: Type[Any], name: str = "field") -> ModelField:
    if model not in _cached_fields:
        _cached_fields[model] = ModelField(
            name=name,
            type_=model,
            class_validators=None,
            model_config=BaseConfig,
            required=True,
        )

    return _cached_fields[model]


def convert(model: Type[InputType], data: Any, loc: str = "data") -> InputType:
    """
    给定任意类型，将提供的数据转化为该类型。主要结合pydantic使用
    """
    field = create_model_field(model)
    value, errors = field.validate(data, {}, loc=(loc,))
    if errors:
        raise ValidationErrorWrap([errors], field.type_)

    return value  # type: ignore[return-value]
