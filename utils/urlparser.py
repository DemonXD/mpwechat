import re
from typing import Union
from urllib.parse import ParseResult, parse_qsl, urlencode, urlparse, urlunparse


class URL:
    """
    封装一个 URL 对象，用于方便的对 URL 进行操作

    :param url: 可传入任意合法的 HTTP URL
    """

    def __init__(self, url: Union[str, ParseResult]):
        if isinstance(url, ParseResult):
            self.parsed = url
        else:
            self.parsed = urlparse(url)

        # 规范化 path
        # * 如果 path 有连续的 /，修改为一个 /
        # * 如果 path 为空，修改为 /
        # 注，如果 path 不以 / 开头，应该在开头加上 /，但这里无需特殊处理，urlunparse 会自动添加
        path = re.sub(r"/+", "/", self.parsed.path) or "/"

        if path != self.parsed.path:
            self.parsed = self.parsed._replace(path=path)

    def replace(self, hash_mode: bool = False, **fields: str) -> "URL":
        if hash_mode:
            if any([k in fields for k in ["scheme", "netloc", "hostname", "port", "uri", "fragment"]]):
                raise ValueError("URL.replace(): hash 模式下不支持修改 scheme、netloc、hostname、port, fragment")
            return self.replace(
                fragment=URL(self.parsed.fragment)
                # 注：mypy 抽风： Argument 1 to "replace" of "URL" has incompatible type "**Dict[str, str]"; expected "bool"
                .replace(**fields).url,  # type: ignore[arg-type]
            )

        if "hostname" in fields or "port" in fields:
            if "netloc" in fields:
                raise ValueError('Can not replace "netloc" together with "hostname" or "port"')

            hostname = fields.get("hostname", self.parsed.hostname)
            port = fields.get("port", self.parsed.port)

            # 如果端口为标准端口则省略掉
            scheme = fields.get("scheme", self.parsed.scheme)
            if scheme == "https" and str(port) == "443":
                port = None
            elif scheme == "http" and str(port) == "80":
                port = None

            netloc = port and f"{hostname}:{port}" or hostname

            fields.pop("hostname", None)
            fields.pop("port", None)
            fields.update(netloc=netloc)  # type: ignore[arg-type]

        # 支持 replace(uri="https://abc.com/def")，uri 表示 query 之前的部分
        if "uri" in fields:
            parsed = urlparse(fields["uri"])
            fields.pop("uri", None)
            fields.update(scheme=parsed.scheme, netloc=parsed.netloc, path=parsed.path)

        return URL(self.parsed._replace(**fields))

    def replace_query(self, hash_mode: bool = False, **fields: str) -> "URL":
        """
        更新 QueryString 中的参数。

        * 更新后，保持原来的参数顺序
        * 若新增参数，则总是添加到结尾
        * 若某个参数值为 None，则删除该参数
        * 若某个参数在 QueryString 中出现多次，只更新第一处（删除时也只删除第一处）

        hash_mode: 许多 SPA 使用 hash 模式，hash 模式下，所有路径、参数都在 # 后面
        """
        if hash_mode:
            return self.replace(
                fragment=URL(self.parsed.fragment)
                # 注：mypy 抽风
                .replace_query(**fields).url,  # type: ignore[arg-type]
            )

        pairs = [[f, v] for (f, v) in parse_qsl(self.parsed.query)]

        for field, value in fields.items():
            found: bool = False
            for pair in pairs:
                if pair[0] == field:
                    pair[1] = value
                    # 找到第一处之后就不需要继续处理后面的了
                    found = True
                    break
            if not found:
                pairs.append([field, value])

        return URL(self.parsed._replace(query=urlencode([(f, v) for (f, v) in pairs if v is not None])))

    @property
    def url(self) -> str:
        return urlunparse(self.parsed)

    def __str__(self):
        return self.url

    def __repr__(self):
        return f'<URL: "{self.url}">'
