from __future__ import unicode_literals

import tweepy
import os
import sys
import secrets

import tweepy
from tweepy import OAuthHandler
from dotenv import load_dotenv

load_dotenv()

REQUEST_HEADERS = {"User-agent": "crush-me-bot 0.0.1dev"}

TWITTER_CONSUMER_KEY = os.getenv("TWITTER_CONSUMER_KEY")
TWITTER_CONSUMER_SECRET = os.getenv("TWITTER_CONSUMER_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET")
SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI", "sqlite:///db.sqlite3")
TWITTER_BOT_ACCOUNT_ID = os.getenv("TWITTER_BOT_ACCOUNT_ID")
MAX_CRUSHER_ITEMS = int(os.getenv("MAX_CRUSHER_ITEMS") or sys.maxsize)
SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex()


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
