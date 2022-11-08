from flask import Blueprint
from .views.biz import biz_route
from .views.checker import checker_route

router = Blueprint("wechatapi", __name__)

router.register_blueprint(biz_route)
router.register_blueprint(checker_route)
