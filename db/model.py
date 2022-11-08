"""
参考 sqlalchemy-mixins 的实现方法，实现一套类似 Django 的 Manager 类。
"""

from typing import Any, ClassVar, Dict, List, Optional, Type, Union

from sqlalchemy import asc, desc, inspect
from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base
from sqlalchemy.ext.hybrid import hybrid_method, hybrid_property
from sqlalchemy.orm import ColumnProperty, Query, RelationshipProperty
from sqlalchemy.orm.attributes import QueryableAttribute
from sqlalchemy.orm.util import AliasedClass
from sqlalchemy.sql import extract, operators

from utils.functional import classproperty

from . import operators as flaskapp_operators
from .exceptions import ObjectDoesNotExist
from .session import DB
from .smartquery import DESC_PREFIX, OPERATOR_SPLITTER, ModelType, SmartQuery


class FlaskAppDeclarativeMeta(DeclarativeMeta):
    def __init__(cls, classname, bases, dict_, **kw):
        super().__init__(classname, bases, dict_, **kw)

        if not cls.__dict__.get("__abstract__", False):
            cls.DoesNotExist = type("DoesNotExist", (ObjectDoesNotExist,), {"model": cls})


BaseModel = declarative_base(metaclass=FlaskAppDeclarativeMeta)


class ReprMixin(BaseModel):
    # 代码摘自 sqlalchemy-mixins
    # https://github.com/absent1706/sqlalchemy-mixins/blob/master/sqlalchemy_mixins/repr.py
    __abstract__ = True

    __repr_attrs__: List[str] = []
    __repr_max_length__ = 15

    @property
    def _id_str(self):
        ids = inspect(self).identity
        if ids:
            return "-".join([str(x) for x in ids]) if len(ids) > 1 else str(ids[0])
        else:
            return "None"

    @property
    def _repr_attrs_str(self):
        max_length = self.__repr_max_length__

        values = []
        single = len(self.__repr_attrs__) == 1
        for key in self.__repr_attrs__:
            if not hasattr(self, key):
                raise KeyError("{} has incorrect attribute '{}' in " "__repr__attrs__".format(self.__class__, key))
            value = getattr(self, key)
            wrap_in_quote = isinstance(value, str)

            value = str(value)
            if len(value) > max_length:
                value = value[:max_length] + "..."

            if wrap_in_quote:
                value = "'{}'".format(value)
            values.append(value if single else "{}:{}".format(key, value))

        return " ".join(values)

    def __repr__(self):
        # get id like '#123'
        id_str = ("#" + self._id_str) if self._id_str else ""
        # join class name, id and repr_attrs
        return "<{} {}{}>".format(
            self.__class__.__name__, id_str, " " + self._repr_attrs_str if self._repr_attrs_str else ""
        )


class InspectionMixin(BaseModel):
    __abstract__ = True

    @classproperty
    def _columns(cls) -> List[str]:
        return inspect(cls).columns.keys()

    @classproperty
    def _primary_keys_full(cls) -> List[ColumnProperty]:
        """Get primary key properties for a SQLAlchemy cls.
        Taken from marshmallow_sqlalchemy
        """
        mapper = cls.__mapper__  # type: ignore[attr-defined]
        return [mapper.get_property_by_column(column) for column in mapper.primary_key]

    @classproperty
    def _primary_keys(cls) -> List[str]:
        return [pk.key for pk in cls._primary_keys_full]

    @classproperty
    def _relations(cls):  # TODO add type annotation
        """Return a `list` of relationship names or the given model"""
        return [c.key for c in cls.__mapper__.iterate_properties if isinstance(c, RelationshipProperty)]

    @classproperty
    def _settable_relations(cls):  # TODO add type annotation
        """Return a `list` of relationship names or the given model"""
        return [r for r in cls._relations if getattr(cls, r).property.viewonly is False]

    @classproperty
    def _hybrid_properties(cls) -> List[str]:
        items = inspect(cls).all_orm_descriptors
        return [item.__name__ for item in items if isinstance(item, hybrid_property)]  # type: ignore[attr-defined]

    @classproperty
    def _hybrid_methods_full(cls):  # TODO add type annotation
        items = inspect(cls).all_orm_descriptors
        return {item.func.__name__: item for item in items if type(item) == hybrid_method}

    @classproperty
    def _hybrid_methods(cls) -> List[str]:
        return list(cls._hybrid_methods_full.keys())

    @classproperty
    def settable_attributes(cls):
        return cls._columns + cls._hybrid_properties + cls._settable_relations


class SmartQueryMixin(InspectionMixin):
    __abstract__ = True

    _operators = {
        "isnull": lambda c, v: (c == None) if v else (c != None),  # noqa
        "exact": operators.eq,  # type: ignore[attr-defined]
        "ne": operators.ne,  # type: ignore[attr-defined]
        "gt": operators.gt,  # type: ignore[attr-defined]
        "ge": operators.ge,  # type: ignore[attr-defined]
        "lt": operators.lt,  # type: ignore[attr-defined]
        "le": operators.le,  # type: ignore[attr-defined]
        "in": operators.in_op,
        "notin": operators.notin_op,
        "between": lambda c, v: c.between(v[0], v[1]),
        "like": operators.like_op,
        "ilike": operators.ilike_op,
        "startswith": operators.startswith_op,
        "istartswith": lambda c, v: c.ilike(v + "%"),
        "endswith": operators.endswith_op,
        "iendswith": lambda c, v: c.ilike("%" + v),
        "contains": lambda c, v: c.ilike("%{v}%".format(v=v)),
        "year": lambda c, v: extract("year", c) == v,
        "year_ne": lambda c, v: extract("year", c) != v,
        "year_gt": lambda c, v: extract("year", c) > v,
        "year_ge": lambda c, v: extract("year", c) >= v,
        "year_lt": lambda c, v: extract("year", c) < v,
        "year_le": lambda c, v: extract("year", c) <= v,
        "month": lambda c, v: extract("month", c) == v,
        "month_ne": lambda c, v: extract("month", c) != v,
        "month_gt": lambda c, v: extract("month", c) > v,
        "month_ge": lambda c, v: extract("month", c) >= v,
        "month_lt": lambda c, v: extract("month", c) < v,
        "month_le": lambda c, v: extract("month", c) <= v,
        "day": lambda c, v: extract("day", c) == v,
        "day_ne": lambda c, v: extract("day", c) != v,
        "day_gt": lambda c, v: extract("day", c) > v,
        "day_ge": lambda c, v: extract("day", c) >= v,
        "day_lt": lambda c, v: extract("day", c) < v,
        "day_le": lambda c, v: extract("day", c) <= v,
        # FastApp operators
        "region_in": flaskapp_operators.region_in,
        "is_today": flaskapp_operators.is_today,
        "is_this_month": flaskapp_operators.is_this_month,
        # "datetime_range": flaskapp_operators.datetime_range,
    }

    @classproperty
    def _filterable_attributes(cls):
        return cls._relations + cls._columns + cls._hybrid_properties + cls._hybrid_methods

    @classproperty
    def _sortable_attributes(cls):
        return cls._columns + cls._hybrid_properties

    @classmethod
    def _filter_expr(cls_or_alias, **filters):
        """
        forms expressions like [Product.age_from = 5,
                                Product.subject_ids.in_([1,2])]
        from filters like {'age_from': 5, 'subject_ids__in': [1,2]}

        Example 1:
            db.query(Product).filter(
                *Product.filter_expr(age_from = 5, subject_ids__in=[1, 2]))

        Example 2:
            filters = {'age_from': 5, 'subject_ids__in': [1,2]}
            db.query(Product).filter(*Product.filter_expr(**filters))


        ### About alias ###:
        If we will use alias:
            alias = aliased(Product) # table name will be product_1
        we can't just write query like
            db.query(alias).filter(*Product.filter_expr(age_from=5))
        because it will be compiled to
            SELECT * FROM product_1 WHERE product.age_from=5
        which is wrong: we select from 'product_1' but filter on 'product'
        such filter will not work

        We need to obtain
            SELECT * FROM product_1 WHERE product_1.age_from=5
        For such case, we can call filter_expr ON ALIAS:
            alias = aliased(Product)
            db.query(alias).filter(*alias.filter_expr(age_from=5))

        Alias realization details:
          * we allow to call this method
            either ON ALIAS (say, alias.filter_expr())
            or on class (Product.filter_expr())
          * when method is called on alias, we need to generate SQL using
            aliased table (say, product_1), but we also need to have a real
            class to call methods on (say, Product.relations)
          * so, we have 'mapper' that holds table name
            and 'cls' that holds real class

            when we call this method ON ALIAS, we will have:
                mapper = <product_1 table>
                cls = <Product>
            when we call this method ON CLASS, we will simply have:
                mapper = <Product> (or we could write <Product>.__mapper__.
                                    It doesn't matter because when we call
                                    <Product>.getattr, SA will magically
                                    call <Product>.__mapper__.getattr())
                cls = <Product>
        """
        if isinstance(cls_or_alias, AliasedClass):
            mapper, cls = cls_or_alias, inspect(cls_or_alias).mapper.class_
        else:
            mapper = cls = cls_or_alias

        expressions = []
        valid_attributes = cls._filterable_attributes
        for attr, value in filters.items():
            # if attribute is filtered by method, call this method
            if attr in cls._hybrid_methods:
                method = getattr(cls, attr)
                expressions.append(method(value, mapper=mapper))
            # else just add simple condition (== for scalars or IN for lists)
            else:
                # determine attribute name and operator
                # if they are explicitly set (say, id___between), take them
                if OPERATOR_SPLITTER in attr:
                    attr_name, op_name = attr.rsplit(OPERATOR_SPLITTER, 1)
                    if op_name not in cls._operators:
                        raise KeyError("Expression `{}` has incorrect " "operator `{}`".format(attr, op_name))
                    op = cls._operators[op_name]
                # assume equality operator for other cases (say, id=1)
                else:
                    attr_name, op = attr, operators.eq

                if attr_name not in valid_attributes:
                    raise KeyError("Expression `{}` " "has incorrect attribute `{}`".format(attr, attr_name))

                column = getattr(mapper, attr_name)
                expressions.append(op(column, value))

        return expressions

    @classmethod
    def _order_expr(cls_or_alias, *columns):
        """
        Forms expressions like [desc(User.first_name), asc(User.phone)]
          from list like ['-first_name', 'phone']

        Example for 1 column:
          db.query(User).order_by(*User.order_expr('-first_name'))
          # will compile to ORDER BY user.first_name DESC

        Example for multiple columns:
          columns = ['-first_name', 'phone']
          db.query(User).order_by(*User.order_expr(*columns))
          # will compile to ORDER BY user.first_name DESC, user.phone ASC

        About cls_or_alias, mapper, cls: read in filter_expr method description
        """
        if isinstance(cls_or_alias, AliasedClass):
            mapper, cls = cls_or_alias, inspect(cls_or_alias).mapper.class_
        else:
            mapper = cls = cls_or_alias

        expressions = []
        for attr in columns:
            fn, attr = (desc, attr[1:]) if attr.startswith(DESC_PREFIX) else (asc, attr)
            if attr not in cls._sortable_attributes:
                raise KeyError("Cant order {} by {}".format(cls, attr))

            expr = fn(getattr(mapper, attr))
            expressions.append(expr)
        return expressions


class Model(ReprMixin, SmartQueryMixin, InspectionMixin, BaseModel):
    """
    Model 基类

    注意，原则上所有 Model 都应当继承该类，如果使用其他方式创建 Model，则没有我们提供的许多边界方法。

    ### `Model._db`

    所有地方都可以通过 `Model._db.session` 来获取 session，等价于 (fastframe.fastapp.db.)`DB.session`，
    省去 import 的麻烦。

    ### `save()`, `delete()`

    提供两个便捷函数，在操作单个 model 时可以快速保存或删除。

    ### `query()`

    类似于 Django 中的 QuerySet，Django 中可以通过 Model.objects.query() 来返回 QuerySet，
    我们则直接通过 `Model.query()` 来返回。

    我们这里不再封装一层 manager。在 Django 中，Manager 的角色有一些尴尬，它的期望是作为 CRUD 的角色来使用，
    但 Manager 是绑定在特定的 Model 上的，使得一些代码难以归纳进去。许多时候，大家使用 Manager 本身只是在用
    queryset 的功能。因此我们这里只封装一个 queryset。

    我们的 SmartQuery 参考 sqlalchemy-mixins 中的实现，提供类似于 Django 的语法，在许多简单的场景下
    可以大大简化代码。

    使用 query() 后，我们的 crud 就不再需要实现成类了，可以直接实现为函数。这将使我们的 crud 代码组织
    变得更加灵活。例如一些操作涉及到多个 Model，放在某一个 Model 的 CRUD 类中都觉得不合适，而实现称函数后，
    这些函数就可以按照业务逻辑去组织了。例如：

    ```py
    # crud/foo.py
    def create_foo(*args) -> Foo:
        return Foo.query().create(...)

    def get_foo(*filter_args) -> Foo:
        return Foo.query().filter(*filter_args)

    def complex_job():
        query = Foo.query().filter(...).query
        query.update({complex update params})
    ```

    在 view 中，可以直接 import 这些方法使用：

    ```py
    # views/foo.py
    from crud.foo import get_foo

    @router.get("/api/foo/{id}", response_model=FooResponse)
    def api_get_foo(id):
        return get_foo(id=id)
    ```
    """

    __abstract__ = True
    __smartquery_class__: Type[SmartQuery] = SmartQuery

    DoesNotExist: ClassVar[Type[ObjectDoesNotExist]]

    _db = DB

    @classmethod
    def query(cls: Type[ModelType], *columns: Any, **filters: Dict[Any, Any]) -> SmartQuery[ModelType]:
        if columns:
            query: Optional[Query] = cls._db.session.query(*columns)
        else:
            query = None

        smart_query = cls.__smartquery_class__(cls, query)

        if filters:
            smart_query = smart_query.filter(**filters)

        return smart_query

    @classmethod
    def filter(cls: Type[ModelType], **filters: Dict[Any, Any]) -> SmartQuery[ModelType]:
        return cls.query().filter(**filters)

    @classmethod
    def order_by(cls: Type[ModelType], *sort_attrs: str) -> SmartQuery[ModelType]:
        return cls.query().order_by(*sort_attrs)

    @classmethod
    def all(cls: Type[ModelType], **filters: Dict[Any, Any]) -> List[ModelType]:
        return cls.query().all(**filters)

    @classmethod
    def first(cls: Type[ModelType], **filters: Dict[Any, Any]) -> Optional[ModelType]:
        return cls.query().first(**filters)

    @classmethod
    def get(cls: Type[ModelType], **filters: Dict[Any, Any]) -> ModelType:
        return cls.query().get(**filters)

    @classmethod
    def one_or_none(cls: Type[ModelType], **filters: Dict[Any, Any]) -> Optional[ModelType]:
        return cls.query().one_or_none(**filters)

    @classmethod
    def count(cls: Type[ModelType]) -> int:
        return cls.query().count()

    @classmethod
    def select_related(cls: Type[ModelType], *fields: Union[str, QueryableAttribute]) -> SmartQuery[ModelType]:
        return cls.query().select_related(*fields)

    def _fill(self: ModelType, **kwargs: Dict[Any, Any]) -> ModelType:
        for name in kwargs.keys():
            if name in self.settable_attributes:
                setattr(self, name, kwargs[name])
            else:
                raise KeyError("Attribute '{}' doesn't exist".format(name))
        return self

    @classmethod
    def create(cls: Type[ModelType], **kwargs: Dict[Any, Any]) -> ModelType:
        model = cls()
        model._fill(**kwargs).save()
        return model

    def update(self, **kwargs: Dict[Any, Any]) -> None:
        self._fill(**kwargs).save()

    def save(self):
        self._db.session.add(self)
        self._db.session.commit()

    def delete(self):
        self._db.session.delete(self)
        self._db.session.commit()
