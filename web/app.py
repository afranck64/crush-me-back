import os
import json
import logging

from flask import Flask, redirect, url_for, render_template, g
from flask_dance.contrib.github import make_github_blueprint, github
from flask_dance.contrib.twitter import make_twitter_blueprint, twitter
from flask_apscheduler import APScheduler
from flask_cors import CORS

from bot.config import (
    TWITTER_ACCESS_TOKEN,
    TWITTER_ACCESS_SECRET,
    TWITTER_CONSUMER_KEY,
    TWITTER_CONSUMER_SECRET,
    SECRET_KEY,
)

from bot.models import Crush, CrushState, get_session, recreate_all, create_all
from bot.cmb import Workflow


create_all()


app = Flask(__name__)
CORS(app)

app.secret_key = SECRET_KEY
blueprint = make_twitter_blueprint(
    api_key=TWITTER_CONSUMER_KEY,
    api_secret=TWITTER_CONSUMER_SECRET,
)
app.register_blueprint(blueprint, url_prefix="/login")

scheduler = APScheduler()

scheduler.api_enabled = False
scheduler.init_app(app)
scheduler.start()


@scheduler.task("cron", id="run_twitter_bot_workflow", minute="*/30")
def run_twitter_bot_workflow():
    flow = Workflow()
    flow.run()


TEST_TWITTER_RESPONSE = os.getenv("TEST_TWITTER_RESPONSE_JSON")
TEST_TWITTER_RESPONSE_JSON = None
if TEST_TWITTER_RESPONSE:
    TEST_TWITTER_RESPONSE_JSON = json.loads(TEST_TWITTER_RESPONSE)


@app.route("/")
def index():
    user_json = None
    matched_crushes = []
    pending_crushes = []

    if TEST_TWITTER_RESPONSE_JSON:
        user_json = TEST_TWITTER_RESPONSE_JSON
    elif twitter.authorized:
        user_json = twitter.get("account/verify_credentials.json").json()

    if user_json is not None:
        user_id = user_json["id_str"]
        with get_session() as session:
            matched_crushes = (
                session.query(Crush).filter((Crush.crusher == user_id) & (Crush.state == CrushState.MATCHED)).all()
            )
            pending_crushes = (
                session.query(Crush).filter((Crush.crusher == user_id) & (Crush.state == CrushState.PENDING)).all()
            )

    g.user = user_json
    g.matched_crushes = matched_crushes
    g.pending_crushes = pending_crushes

    return render_template("base.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html", app_name="crush-me-back", contact="https://twitter.com/CrushMeBackBot")


@app.route("/terms")
def terms():
    return render_template("terms.html", app_name="crush-me-back", contact="https://twitter.com/CrushMeBackBot")


if __name__ == "__main__":
    gunicorn_logger = logging.getLogger("gunicorn.error")
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
    app.run(port=5000)
