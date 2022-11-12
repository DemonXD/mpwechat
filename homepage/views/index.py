from flask import Blueprint, render_template

home_router = Blueprint("homepage", __name__)


@home_router.get("/home")
def page_home():
    return render_template("index.html")
