from flask import Blueprint
from homepage.views.index import home_router

router = Blueprint(
    "homepage", 
    __name__
)

router.register_blueprint(home_router)