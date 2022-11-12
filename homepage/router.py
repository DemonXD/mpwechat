from flask import Blueprint
from homepage.views.index import home_router
from homepage.views.management import manager_route

router = Blueprint("homepage", __name__)

router.register_blueprint(home_router)
router.register_blueprint(manager_route)
