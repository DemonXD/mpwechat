import re


def render_content(content: str, paras: dict) -> str:
    """固定模版渲染
    Sample:
        content: "这里是一个变量:${var}, 这里是一个名称:${name}"
        paras: {"var": "variable", "name": "namespace"}
    """
    KEY_PATTERN = re.compile(r"\${(?P<key>[^}]+)}")

    return re.sub(KEY_PATTERN, lambda p: paras[p.group("key")], content)


if __name__ == "__main__":
    content = "这里是一个变量:${var}, 这里是一个名称:${name}"
    paras = {"var": "variable", "name": "namespace"}

    result = render_content(content, paras)
    assert result == "这里是一个变量:variable, 这里是一个名称:namespace"
    print(result)
