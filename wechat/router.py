from flask import Blueprint
from .views.checker import checker_route

router = Blueprint("wechatapi", __name__, url_prefix="/api")

router.register_blueprint(checker_route)
