from flask import Blueprint
from .views.biz import biz_route
from .views.checker import checker_route

router = Blueprint("wechatapi", __name__, url_prefix="/api")

router.register_blueprint(biz_route)
router.register_blueprint(checker_route)
