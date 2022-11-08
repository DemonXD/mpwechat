from flask import Blueprint, jsonify

checker_route = Blueprint("checker", __name__, url_defaults="/checker")

@checker_route.route("/", methods=["GET"])
def api_checker():
    return jsonify({})


