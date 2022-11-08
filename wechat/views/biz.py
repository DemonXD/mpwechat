from flask import Blueprint, jsonify

biz_route = Blueprint("biz", __name__, url_prefix="/api")

@biz_route.route("/ping", methods=["GET"])
def api_ping_pong():
    return jsonify({"msg": "pong"})