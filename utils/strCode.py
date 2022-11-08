"""
组织架构编码处理库，该库后续可迁移到 ns-researchforce-sdk 中
"""

from functools import cached_property
from typing import TYPE_CHECKING, List, Type, TypeVar

CodeType = TypeVar("CodeType", bound="BaseCode")


class BaseCode:
    """
    基础类，该类默认默认配置为20位编码、级宽2位、最大10级。实际使用时，应当继承该类，生成专用的类使用。

    NOTE：将来考虑实现一个工厂函数：
    FooCode = BaseCode.from_config(level_width=2, max_level=10)
    """

    # 级宽
    LEVEL_LENGTH: int = 2
    # 最大级数
    MAX_LEVEL: int = 10

    # 以下是一些（可通过计算得出的）常用值，事先计算好
    CODE_LENGTH: int = LEVEL_LENGTH * MAX_LEVEL
    ZERO_CODE: str = "0" * LEVEL_LENGTH
    ROOT_CODE: str = "0" * CODE_LENGTH

    def __init__(self, code: str):
        if code == "root":
            code = self.ROOT_CODE

        if len(code) != self.CODE_LENGTH or not code.isdigit():
            # NOTE 后续考虑如何支持字母的情况
            raise ValueError(f"无效的编码，编码长度必须为 {self.CODE_LENGTH}，且全部为数字")

        self.code: str = code

    @cached_property
    def level(self) -> int:
        """
        返回当前编码的级别，返回值为 0..MAX_LEVEL
        """
        level = self.MAX_LEVEL
        while self.code[self.LEVEL_LENGTH * (level - 1) : self.LEVEL_LENGTH * level] == self.ZERO_CODE:
            level -= 1

        return level

    @cached_property
    def prefix(self) -> str:
        """
        返回从顶级至本级的编码，如 1230000000 -> 1230
        """
        return self.code[: self.level * self.LEVEL_LENGTH]

    @cached_property
    def postfix(self) -> str:
        """
        返回本级别之后的所有 0，如  1230000000 -> 000000
        """
        return (self.MAX_LEVEL - self.level) * self.ZERO_CODE

    @cached_property
    def children_postfix(self) -> str:
        """
        返回子节点的后缀。

        当需要获取某父节点的所有子节点时，可用以下条件筛选
        startswith=parent.prefix, endswith=parent.children_postfix
        """
        return (self.MAX_LEVEL - self.level - 1) * self.ZERO_CODE

    @cached_property
    def level_code(self) -> str:
        """
        返回本级的编码
        """
        return self.code[(self.level - 1) * self.LEVEL_LENGTH : self.level * self.LEVEL_LENGTH]

    @cached_property
    def next_code(self) -> str:
        """
        返回该编码的下一个编码
        """
        if self.level_code == "9" * self.LEVEL_LENGTH:
            raise ValueError("当前编码已达最大值")
        next_level_code = int(self.level_code) + 1
        return (
            self.code[: (self.level - 1) * self.LEVEL_LENGTH]
            + f"{next_level_code:0{self.LEVEL_LENGTH}}"
            + self.code[self.level * self.LEVEL_LENGTH :]
        )

    @cached_property
    def next(self: "CodeType") -> "CodeType":
        return self.__class__(self.next_code)

    @cached_property
    def first_child_code(self) -> str:
        """
        获取第一个子节点的编码
        """
        if self.level == self.MAX_LEVEL:
            raise ValueError("当前编码级别已满，没有子节点")
        return self.prefix + ("0" * (self.LEVEL_LENGTH - 1)) + "1" + self.ZERO_CODE * (self.MAX_LEVEL - self.level - 1)

    @cached_property
    def first_child(self: "CodeType") -> "CodeType":
        return self.__class__(self.first_child_code)

    @cached_property
    def parent_code(self) -> str:
        """
        返回该编码的父节点编码
        """
        if self.level < 1:
            raise ValueError("当前编码为根节点，没有父节点")

        return self.code[: (self.level - 1) * self.LEVEL_LENGTH] + self.ZERO_CODE * (self.MAX_LEVEL - self.level + 1)

    @cached_property
    def parent(self: "CodeType") -> "CodeType":
        return self.__class__(self.parent_code)

    @classmethod
    def from_config(cls, name: str, level_length: int = 2, max_level: int = 10) -> Type["CodeType"]:
        return type(
            name,
            (cls,),
            {
                "LEVEL_LENGTH": level_length,
                "MAX_LEVEL": max_level,
                "CODE_LENGTH": level_length * max_level,
                "ZERO_CODE": "0" * level_length,
            },
        )

    @cached_property
    def stack_codes(self) -> List[str]:
        """
        返回根节点至该节点的所有编码
        """
        if self.level == 0:
            return []
        if self.level == 1:
            return [self.code]
        else:
            return self.parent.stack_codes + [self.code]


if TYPE_CHECKING:

    class OrgCode(BaseCode):
        pass

else:
    OrgCode: Type[BaseCode] = BaseCode.from_config("OrgCode", level_length=2, max_level=10)

# print(OrgCode("00000000000000000000").next_code)
