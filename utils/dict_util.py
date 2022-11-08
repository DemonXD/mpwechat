import copy
from typing import Any, Dict, List, Optional, TypeVar, Union

# class DictKeyError(KeyError):
#     pass


T = TypeVar("T")
U = TypeVar("U")
V = TypeVar("V")
W = TypeVar("W")


EmptyList = List[Any]

# 用户输入数据
TargetItemType = Dict[T, U]
BlankTemplateType = Dict[T, V]
PathType = List[Any]
PathlistType = List[PathType]
FinalType = Dict[T, W]


class MergeDictTool:
    """
    @Date:          4/28/2020, 17:11
    @author:        "Miles Xu"
    @copyright:     "Copyright 2020, The DM Project"
    @credits:       ["Miles Xu", ]
    @license:       "MIT"
    @version:       "0.0.2"
    @maintainer:    "Miles Xu"
    @email:         "kanonxmm@163.com"
    @status:        "Development"
    @condition:
        input: list of dict, every dict has the same structure and same keys
    @feature:
        merge multi level dict's value, sample:
        input:
            [
                {"field": {"column": {"n1": "v1", "n2": "v2"}}},
                {"field": {"column": {"n1": "v3", "n2": "v4"}}},
                {"field": {"column": {"n1": "v5", "n2": "v6"}}},
            ]

        return:
            {"field": {"column": {"n1": ["v1", "v3", "v5"],"n2": ["v2", "v4", "v6"]}}}
    """

    def __init__(self, targetsList: Optional[List[TargetItemType]] = None) -> None:
        self.pathlist: PathlistType = []
        self.blanktemplate: FinalType = {}
        self.pre_result: FinalType = {}
        if targetsList is not None and targetsList != []:
            self.analysisPath(targetsList[0])
            self.blanktemplate = self.buildblankdict()
            self.targetlist = targetsList
            self.pre_result = copy.deepcopy(self.blanktemplate)
            self.combine()

    def analysisPath(self, sampleitem: TargetItemType, singletemppath: Optional[PathType] = None) -> None:
        """
        Desc. : according to the sampleitem to analysis all path, base to DFS
        :input sampleitem:
        :input singletemppath:

        self.pathlist ->
            [["field", "column", "n1"], ["field", "column", "n2"], [...] ...]
        """
        for key, val in sampleitem.items():
            singlepath = copy.deepcopy(singletemppath) if singletemppath is not None else []
            if isinstance(val, dict):
                singlepath.append(key)
                self.analysisPath(val, singlepath)
            else:
                singlepath.append(key)
                self.pathlist.append(singlepath)

    def buildblankdict(self) -> BlankTemplateType:
        """
        Desc. : according to self.pathlist to build a blank dict
        :input res: origin dict
        :return : dict of cleared value
        """
        temp_results: List[BlankTemplateType] = []
        results: BlankTemplateType = {}
        for path in self.pathlist:
            temp_path = copy.deepcopy(path)
            temp_path.reverse()
            value: EmptyList = []
            middle: BlankTemplateType = {}
            for key in temp_path:
                result: BlankTemplateType = {}
                if middle == {}:
                    result[key] = value
                    middle = result
                    continue
                result[key] = middle
                middle = result
            temp_results.append(middle)
        for each in temp_results:
            results = self._merge_dict(results, each)
        return results

    def getPathValue(self, singleitem: TargetItemType, path: PathType) -> Any:
        """
        :input singleitem: the item of targetsList
        :input path: the list of key, like: ["field", "column", "n1"]
        :return : return the value of input path in singleitem
        根据提供的path路径，获取对应的值
        默认情况下所有的singleitem层级都是相同的，不需要另外判断
        """
        result: Any = None
        for each_key in path:
            if result is None:
                result = singleitem[each_key]
                continue
            if isinstance(result, dict):
                result = result[each_key]

        if result is None or isinstance(result, dict):
            raise ValueError("空值错误或者值类型错误(也可能是层级不匹配)")

        return result

    def setPathValue(self, result: FinalType, path: PathType, value: Any) -> None:
        """
        Desc. : fill the value to the specified path of result
        :input result: origin dict to be filled with value
        :input value: the value to be filled
        """
        temp_result: Union[List, FinalType] = {}

        for key in path:
            if temp_result == {}:
                temp_result = result[key]
                if isinstance(temp_result, list):
                    break
                elif isinstance(temp_result, dict):
                    continue
                else:
                    raise ValueError("值类型错误")
            temp_result = temp_result[key]

        assert type(temp_result) == list, f"值类型错误=>{type(temp_result)}"

        if isinstance(value, (list, tuple, set)):
            temp_result.extend(list(value))
        else:
            temp_result.append(value)

    def statistic(self, result: FinalType) -> None:
        """
        Desc.: Calculate the min, max, median value for each key
        :input result: origin dict
        :return None:
        """
        for key, val in result.items():
            if isinstance(val, dict):
                self.statistic(val)
            elif isinstance(val, list):
                if all([isinstance(each, (int, float)) for each in val]):
                    result[key] = [min(val), sorted(val)[len(val) // 2], max(val)]

    def addItem(self, item: TargetItemType) -> None:
        if item == {}:
            return None
        if self.pathlist == []:
            self.analysisPath(item)

        if self.pre_result == {}:
            self.pre_result = copy.deepcopy(self.blanktemplate)

        for path in self.pathlist:
            try:
                value = self.getPathValue(item, path)
            except ValueError:
                return None
            else:
                self.setPathValue(self.pre_result, path, value)

    def combine(self) -> Optional[FinalType]:
        if self.pathlist is not []:
            result = self.blanktemplate
            for each_item in self.targetlist:
                for each_path in self.pathlist:
                    value = self.getPathValue(each_item, each_path)
                    self.setPathValue(result, each_path, value)
            # self.statistic(result)
            return result
        return None

    def _merge_dict(self, a: FinalType, b: FinalType, *others: FinalType) -> FinalType:
        """
        单纯的merge 两个dict，相同key会覆盖
        """
        dst = a.copy()
        for k, v in b.items():
            if k in dst and isinstance(dst[k], dict) and isinstance(b[k], dict):
                dst[k] = self._merge_dict(dst[k], b[k])
            else:
                dst[k] = b[k]
        if others:
            return self._merge_dict(dst, *others)
        else:
            return dst


if __name__ == "__main__":
    single_sample = [
        {"name1": 1, "name2": 2, "name3": 3},
        {"name1": 2, "name2": 3, "name3": 4},
        {"name1": 3, "name2": 4, "name3": 5},
        {"name1": 4, "name2": 5, "name3": 6},
    ]
    sample = [
        {"field": {"column1": {"n1": {"m1": 10}, "n2": 15}, "column2": 3}},
        {"field": {"column1": {"n1": {"m1": 15}, "n2": 20}, "column2": 6}},
        {"field": {"column1": {"n1": {"m1": 20}, "n2": 10}, "column2": 9}},
    ]
    sample2 = [
        {
            "field": {
                "column1": {"n1": {"m1": "v1"}, "n2": "v2"},
                "column2": {"n3": "v~"},
            }
        },
        {
            "field": {
                "column1": {"n1": {"m1": "v3"}, "n2": "v4"},
                "column2": {"n3": "v^"},
            }
        },
        {
            "field": {
                "column1": {"n1": {"m1": "v5"}, "n2": "v6"},
                "column2": {"n3": "v*"},
            }
        },
    ]

    print(MergeDictTool(single_sample).combine())
    print(MergeDictTool(sample).combine())
    print(MergeDictTool(sample2).combine())
