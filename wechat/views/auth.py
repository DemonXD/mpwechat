'''
TODO: 实现微信认证

def is_hash_mode_url(url: str):
    return re.compile(r"/#/").findall(url) != []


class WebAuthParams(BaseModel):
    redirect_uri: Optional[str] = Field(None)
    appid: Optional[str] = Field(None)
    state: Optional[str] = Field(None)
    code: Optional[str] = Field(None)
    scope: str = Field("snsapi_base")
    isMp: str = Field("false")
    response_type: str = Field("code")

    Query: ClassVar[Callable] = QueryDep()


@router.get("/webauth", summary="微信 Web 授权中转接口")
def webauth(
    request: Request,
    params: WebAuthParams = Depends(WebAuthParams.Query),
):
    """
    微信 Web 授权中转接口
    """
    url: URL

    # 无论来自应用还是来自微信回跳，都必须有 redirect_uri 参数
    # TODO，对于来自应用的，我们以后应当添加域名白名单
    if not params.redirect_uri:
        raise text.Plain(status_code=400, content="参数错误")

    # 如果不含 Code，则表示来自应用，需要跳转到微信，跳转时应带上所有参数，
    # 此时，只需要将原来的 url （不含 querystring）部分替换成微信的地址即可。
    # 此前实现的 portal.einmatrix.com 中，会允许应用不携带 scope, response_type 参数，
    # 由 portal 自动添加，因此这里也做同样的处理。
    if not params.code:
        # url 为要跳转出去的地址（该分支下为微信地址）
        url = URL(request.url._url)

        if params.scope == "snsapi_login" and params.isMp != "true":
            # "https://open.weixin.qq.com/connect/qrconnect"
            url = url.replace(uri="https://open.weixin.qq.com/connect/qrconnect")
        else:
            # "https://open.weixin.qq.com/connect/oauth2/authorize#wechat_redirect"
            url = url.replace(uri="https://open.weixin.qq.com/connect/oauth2/authorize#wechat_redirect")

        url = url.replace_query(scope=params.scope, response_type=params.response_type, redirect_uri=request.url._url)
    else:
        # 包含code，表示来自微信，需要跳转到应用
        # 此时这里可能是普通的后端应用或者网页应用
        # 也可能是SPA的hash mode应用，所以要做区别对url进行处理
        url = URL(params.redirect_uri)
        hash_mode = False
        if is_hash_mode_url(url.url):
            hash_mode = True
        url = url.replace_query(
            code=params.code,
            state=params.state if params.state is not None else "",
            hash_mode=hash_mode,
        )

    # 返回url供上游自行处理
    return text.Plain(status_code=200, content=str(url))
    # return redirect.Temporary(str(url))

'''

