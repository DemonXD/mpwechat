import hashlib
from typing import List
from flask import Blueprint, request, make_response
from pydantic import BaseModel
from wechat.conf import settings as wechat_settings
from responses import api


checker_route = Blueprint("checker", __name__)


class CheckParams(BaseModel):
    signature: str
    timestamp: str
    nonce: str
    echostr: str


@checker_route.route("/check_token", methods=["GET"])
def api_checker():
    check_token = wechat_settings.local.bind_service_token
    if check_token is None:
        raise ValueError("未设置微信公众平台token")

    params = CheckParams(**request.args.to_dict())

    timestamp = params.timestamp
    nonce = params.nonce
    temp_list: List[str] = [check_token, timestamp, nonce]
    temp_list.sort()
    checks = "".join(temp_list)
    sha1check = hashlib.sha1()
    sha1check.update(checks.encode("utf-8"))
    hashcode = sha1check.hexdigest()
    if hashcode == params.signature:
        resp = make_response(params.echostr, 200)
        resp.mimetype = "text/plain"
        return resp
    else:
        return api.BadRequest(message="参数错误")
