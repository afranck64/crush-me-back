import logging
from flask import Flask, redirect, url_for
from flask_dance.contrib.github import make_github_blueprint, github
from flask_dance.contrib.twitter import make_twitter_blueprint, twitter

from bot.config import TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET, TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET

import time

from bot.models import Crush, CrushState, get_session, recreate_all, create_all

create_all()

app = Flask(__name__)
app.secret_key = "supersekrit"  # Replace this with your own secret!
blueprint = make_twitter_blueprint(
    api_key=TWITTER_CONSUMER_KEY,
    api_secret=TWITTER_CONSUMER_SECRET,
)
app.register_blueprint(blueprint, url_prefix="/login")


from flask import render_template


@app.route("/")
def index():
    with get_session() as session:
        # crushes = session.query(Crush).all()
        # print("CRUSHES: ", crushes)
        # res = "<br>".join(str([crush.crusher, "->", crush.crushee]) for crush in crushes)
        # print("RES: ", res)
        nb_crushes = session.query(Crush).count()
        res = f"""<h1> Crush me back! </h1>
        Registered crushes: <strong>{nb_crushes}</strong>
        """

    if not res:
        res = "Found nothing in the database!!"

    return render_template("base.html")
    return res


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


if __name__ == "__main__":
    gunicorn_logger = logging.getLogger("gunicorn.error")
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
    app.run(port=5000)
