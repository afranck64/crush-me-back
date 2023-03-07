from __future__ import unicode_literals

import tweepy
import os
import random

import tweepy
from tweepy import OAuthHandler
from dotenv import load_dotenv

load_dotenv()


# def get_env_int(key, default=0):
#     try:
#         return int(os.getenv(key))
#     except Exception:
#         return default


REQUEST_HEADERS = {"User-agent": "crush-me-bot 0.0.1dev"}

TWITTER_CONSUMER_KEY = os.getenv("TWITTER_CONSUMER_KEY")
TWITTER_CONSUMER_SECRET = os.getenv("TWITTER_CONSUMER_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET")
SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI", "sqlite:///db.sqlite3")
TWITTER_BOT_ACCOUNT_ID = os.getenv("TWITTER_BOT_ACCOUNT_ID")


def check_config():
    assert TWITTER_CONSUMER_KEY, "TWITTER_CONSUMER_KEY not set"
    assert TWITTER_CONSUMER_SECRET, "TWITTER_CONSUMER_SECRET not set"
    assert TWITTER_ACCESS_TOKEN, "TWITTER_ACCESS_TOKEN not set"
    assert TWITTER_ACCESS_SECRET, "TWITTER_ACCESS_SECRET not set"
    assert SQLALCHEMY_DATABASE_URI, "SQLALCHEMY_DATABASE_URI not set"
    assert TWITTER_BOT_ACCOUNT_ID, "TWITTER_BOT_ACCOUNT_ID not set"


def get_api():
    auth = OAuthHandler(TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET)
    auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET)

    return tweepy.API(auth, wait_on_rate_limit=True)


check_config()
