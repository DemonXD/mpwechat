from collections import OrderedDict
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generic,
    Iterable,
    List,
    Literal,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from sqlalchemy.orm import Query, aliased, contains_eager, joinedload, subqueryload
from sqlalchemy.orm.attributes import InstrumentedAttribute, QueryableAttribute
from sqlalchemy.orm.exc import MultipleResultsFound

from .exceptions import MultipleObjectsReturned

if TYPE_CHECKING:
    from .model import InspectionMixin, Model

ModelType = TypeVar("ModelType", bound="Model")
SmartQueryType = TypeVar("SmartQueryType", bound="SmartQuery")

JoinMethodType = Literal["joined", "subquery"]
EagerSchemaType = Dict[  # type: ignore[misc]
    Union[str, QueryableAttribute],
    Union[Tuple[JoinMethodType, "EagerSchemaType"], "EagerSchemaType", JoinMethodType],  # type: ignore[misc]
]
EagerFlatSchemaType = Dict[str, JoinMethodType]

CustomQueryBuilder = Callable[[Query], Query]


RELATION_SPLITTER = "___"
OPERATOR_SPLITTER = "__"
DESC_PREFIX = "-"
JOINED = "joined"
SUBQUERY = "subquery"


class SmartQuery(Generic[ModelType]):
    """
    参考 Django 的思路，实现一个 QuerySet 类，该 QuerySet 的实现参考 sqlalchemy-mixins
    的 smartquery。
    """

    def __init__(self, model: Type[ModelType], query: Optional[Query] = None):
        self.model: Type[ModelType] = model
        self._query: Optional[Query] = query

    @property
    def query(self) -> Query:
        if self._query is None:
            self._query = self.model._db.session.query(self.model)
        return self._query

    def filter(self: SmartQueryType, **filters: Dict[Any, Any]) -> SmartQueryType:
        return self.__class__(self.model, smart_query(self.query, filters=filters))

    def order_by(self: SmartQueryType, *sort_attrs: str) -> SmartQueryType:
        return self.__class__(self.model, smart_query(self.query, sort_attrs=sort_attrs))

    def all(self, **filters: Dict[Any, Any]) -> List[ModelType]:
        if filters:
            return self.filter(**filters).all()

        return self.query.all()

    def first(self, **filters: Dict[Any, Any]) -> Optional[ModelType]:
        if filters:
            return self.filter(**filters).first()

        return self.query.first()

    def get(self, **filters: Dict[Any, Any]) -> ModelType:
        if filters:
            return self.filter(**filters).get()

        try:
            obj = self.query.one_or_none()
        except MultipleResultsFound:
            raise MultipleObjectsReturned()
        if not obj:
            raise self.model.DoesNotExist()
        return obj

    def one_or_none(self, **filters: Dict[Any, Any]) -> Optional[ModelType]:
        if filters:
            return self.filter(**filters).one_or_none()
        return self.query.one_or_none()

    def delete(self):
        return self.query.delete()

    def count(self) -> int:
        return self.query.count()

    def select_related(self: SmartQueryType, *fields: Union[str, QueryableAttribute]) -> SmartQueryType:
        return self.__class__(
            self.model,
            smart_query(
                self.query,
                schema={v: JOINED for v in fields},
            ),
        )

    def custom_query(self: SmartQueryType, build_query: CustomQueryBuilder) -> SmartQueryType:
        """
        有些情况，SmartQuery 无法满足需求，过程中需要由外部来进一步构造请求，
        外部构造完请求后，可以设置一个新的 SmartQuery 对象。例如：

            sq = FooModel.filter(key1=val1, key2=val2)
            if is_expired is True:
                sq = sq.filter(expires__lt=int(time.time()))
            elif is_expired is False:
                sq = sq.custom_query(
                    lambda query: query.filter(
                        or_(
                            FooModel.expires.is_(None),
                            FooModel.expires > int(time.time()),
                        )
                    )
                )
            return sq
        """
        return self.__class__(self.model, build_query(self.query))

    def sa_filter(self: SmartQueryType, *args: Any) -> SmartQueryType:
        """
        调用 SQLAlchemy Query 的 filter() 方法
        """
        return self.custom_query(lambda query: query.filter(*args))

    # TODO：为 SQLAlchemy Query 所有常用方法都添加封装，这些方法都以 sa_ 开头


## 以下代码主要摘自 sqlalchemy-mixins，根据实现不同稍微做了调整


def _parse_path_and_make_aliases(
    entity: "InspectionMixin", entity_path: str, attrs: List[str], aliases: Dict[str, Tuple]
) -> None:
    """
    :type entity: InspectionMixin
    :type entity_path: str
    :type attrs: list
    :type aliases: OrderedDict

    Sample values:

    attrs: ['product__subject_ids', 'user_id', '-group_id',
            'user__name', 'product__name', 'product__grade_from__order']
    relations: {'product': ['subject_ids', 'name'], 'user': ['name']}

    """
    relations: Dict[str, List[str]] = {}
    # take only attributes that have magic RELATION_SPLITTER
    for attr in attrs:
        # from attr (say, 'product__grade__order')  take
        # relationship name ('product') and nested attribute ('grade__order')
        if RELATION_SPLITTER in attr:
            relation_name, nested_attr = attr.split(RELATION_SPLITTER, 1)
            if relation_name in relations:
                relations[relation_name].append(nested_attr)
            else:
                relations[relation_name] = [nested_attr]

    for relation_name, nested_attrs in relations.items():
        path = entity_path + RELATION_SPLITTER + relation_name if entity_path else relation_name
        if relation_name not in entity._relations:
            raise KeyError(
                "Incorrect path `{}`: " "{} doesnt have `{}` relationship ".format(path, entity, relation_name)
            )
        relationship = getattr(entity, relation_name)
        alias = aliased(relationship.property.mapper.class_)
        aliases[path] = alias, relationship
        _parse_path_and_make_aliases(alias, path, nested_attrs, aliases)  # type: ignore[arg-type]


def _get_root_cls(query: Query) -> ModelType:
    # sqlalchemy < 1.4.0
    if hasattr(query, "_entity_zero"):
        return query._entity_zero().class_  # type: ignore[attr-defined]

    # sqlalchemy >= 1.4.0
    else:
        if hasattr(query, "_entity_from_pre_ent_zero"):
            return query._entity_from_pre_ent_zero().class_  # type: ignore[attr-defined]
    raise ValueError("Cannot get a root class from`{}`".format(query))


def smart_query(
    query: Query,
    filters: Optional[Dict[str, Any]] = None,
    sort_attrs: Optional[Iterable[str]] = None,
    schema: Optional[EagerSchemaType] = None,
) -> Query:
    """
    Does magic Django-ish joins like post___user___name__startswith='Bob'
     (see https://goo.gl/jAgCyM)
    Does filtering, sorting and eager loading at the same time.
    And if, say, filters and sorting need the same joinm it will be done
     only one. That's why all stuff is combined in single method

    :param query: sqlalchemy.orm.query.Query
    :param filters: dict
    :param sort_attrs: List[basestring]
    :param schema: dict
    """
    if not filters:
        filters = {}
    if not sort_attrs:
        sort_attrs = []

    #  Load schema early since we need it to check whether we should eager load a relationship
    if schema:
        flat_schema = _flatten_schema(schema)
        # print(flat_schema)
    else:
        flat_schema = {}

    # sqlalchemy >= 1.4.0, should probably a. check something else to determine if we need to convert
    # AppenderQuery to a query, b. probably not hack it like this
    # noinspection PyProtectedMember
    if type(query).__name__ == "AppenderQuery" and query._statement:  # type: ignore[attr-defined]
        sess = query.session
        # noinspection PyProtectedMember
        query = query._statement  # type: ignore[attr-defined]
        query.session = sess

    root_cls: Type[Model] = _get_root_cls(query)  # for example, User or Post
    attrs = list(filters.keys()) + list(map(lambda s: s.lstrip(DESC_PREFIX), sort_attrs))
    aliases: Dict[str, Tuple] = OrderedDict({})
    _parse_path_and_make_aliases(root_cls, "", attrs, aliases)  # type: ignore[arg-type]

    loaded_paths = []
    for path, al in aliases.items():
        relationship_path = path.replace(RELATION_SPLITTER, ".")
        if not (relationship_path in flat_schema and flat_schema[relationship_path] == SUBQUERY):
            query = query.outerjoin(al[0], al[1]).options(contains_eager(relationship_path, alias=al[0]))
            loaded_paths.append(relationship_path)

    for attr, value in filters.items():
        if RELATION_SPLITTER in attr:
            parts = attr.rsplit(RELATION_SPLITTER, 1)
            entity, attr_name = aliases[parts[0]][0], parts[1]
        else:
            entity, attr_name = root_cls, attr
        try:
            query = query.filter(*entity._filter_expr(**{attr_name: value}))
        except KeyError as e:
            raise KeyError("Incorrect filter path `{}`: {}".format(attr, e))

    for attr in sort_attrs:
        if RELATION_SPLITTER in attr:
            prefix = ""
            if attr.startswith(DESC_PREFIX):
                prefix = DESC_PREFIX
                attr = attr.lstrip(DESC_PREFIX)
            parts = attr.rsplit(RELATION_SPLITTER, 1)
            entity, attr_name = aliases[parts[0]][0], prefix + parts[1]
        else:
            entity, attr_name = root_cls, attr
        try:
            query = query.order_by(*entity._order_expr(attr_name))
        except KeyError as e:
            raise KeyError("Incorrect order path `{}`: {}".format(attr, e))

    if flat_schema:
        not_loaded_part = {path: v for path, v in flat_schema.items() if path not in loaded_paths}
        query = query.options(*_eager_expr_from_flat_schema(not_loaded_part))

    return query


def eager_expr(schema: EagerSchemaType) -> list:
    """
    :type schema: dict
    """
    flat_schema = _flatten_schema(schema)
    return _eager_expr_from_flat_schema(flat_schema)


def _flatten_schema(schema: EagerSchemaType) -> EagerFlatSchemaType:
    """
    :type schema: dict
    """

    def _flatten(schema: EagerSchemaType, parent_path: str, result: EagerFlatSchemaType) -> None:
        """
        :type schema: dict
        """
        for path, value in schema.items():
            # for supporting schemas like Product.user: {...},
            # we transform, say, Product.user to 'user' string
            if isinstance(path, InstrumentedAttribute):
                path = path.key

            if isinstance(value, tuple):
                join_method, inner_schema = value[0], value[1]
            elif isinstance(value, dict):
                join_method, inner_schema = JOINED, value
            else:
                join_method, inner_schema = value, None

            full_path: str = parent_path + "." + path if parent_path else path  # type: ignore[assignment]
            result[full_path] = join_method

            if inner_schema:
                _flatten(inner_schema, full_path, result)

    result: EagerFlatSchemaType = {}
    _flatten(schema, "", result)
    return result


def _eager_expr_from_flat_schema(flat_schema: EagerFlatSchemaType) -> list:
    """
    :type flat_schema: dict
    """
    result = []
    for path, join_method in flat_schema.items():
        if join_method == JOINED:
            result.append(joinedload(path))
        elif join_method == SUBQUERY:
            result.append(subqueryload(path))
        else:
            raise ValueError("Bad join method `{}` in `{}`".format(join_method, path))
    return result
