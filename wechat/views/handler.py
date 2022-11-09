from flask import Blueprint


handler_router = Blueprint("handler", __name__)


@handler_router.route("/check_token", methods=["POST"])
def api_handler():
    # TODO: 实现公众号消息回复
    ...