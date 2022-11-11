from flask import render_template, Blueprint

home_router = Blueprint("homepage", __name__)


@home_router.get("/home")
def page_home():
    return render_template("homepage/index.html")
