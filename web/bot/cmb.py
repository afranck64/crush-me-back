# Crush-me-back bot
from re import match
import warnings
from sqlalchemy import exc
import tweepy
from tweepy.models import DirectMessage
from sqlalchemy.orm import aliased
import sys
import logging

from .config import TWITTER_BOT_ACCOUNT_ID, get_api, MAX_CRUSHER_ITEMS
from .models import Crush, CrushState, get_session, recreate_all, Session

logger = logging.getLogger(__name__)

"""
Alice: -> Bob, Eve
Anna: -> Bob
Bob: -> Alice, Anna, Eve
Eve: -> Alice, Anna

# Crushes
{Alice, Bob}, {Alice, Eve}, {Anna, Bob}

## Flow:
on new messages:

pending -> matched -> notified
- register crushes
- [delete] crush messages
- collect matching crushes
- notify matching crushes
- [delete] crush notification messages
- cleanup database
"""

GET_DIRECT_MESSAGES_MAX_COUNT = 50


class Bot(object):
    def __init__(
        self,
        *,
        api: tweepy.API,
        session_getter: "callable" = None,
        twitter_bot_account_id: str = None,
        max_crusher_items: int = None,
    ):
        """_summary_

        Args:
            api (tweepy.API): _description_
            session_getter (callable, optional): _description_. Defaults to None.
            twitter_bot_account_id (str, optional): _description_. Defaults to None.
            max_crusher_items (int, optional): _description_. Defaults to None.
        """
        if session_getter is None:
            session_getter = get_session
        if twitter_bot_account_id is None:
            twitter_bot_account_id = TWITTER_BOT_ACCOUNT_ID
        if max_crusher_items is None:
            max_crusher_items = MAX_CRUSHER_ITEMS

        self.api = api
        self.session_getter = session_getter
        self.twitter_bot_account_id = twitter_bot_account_id
        self.max_crusher_items = max_crusher_items

    def do_get_session(self) -> Session:
        return self.session_getter()

    def do_send_direct_message(self, recipient_id: str, text: str):
        self.api.send_direct_message(
            recipient_id=recipient_id,
            text=text,
        )

    def do_get_direct_messages(self, count: int = GET_DIRECT_MESSAGES_MAX_COUNT):
        messages = self.api.get_direct_messages(count=count)
        return messages

    def process_message(self, message: DirectMessage) -> "tuple[str,list[str]]":
        logger.debug(f"Processing message: {message._json['id']}")
        message_id = message._json["id"]
        with self.do_get_session() as session:
            message_already_processed = session.query(Crush).filter(Crush.message_id == message_id).first()
        if message_already_processed:
            warnings.warn(f"message with id: {message_id} has already been processed by the system.")
            return None, []

        # TODO: check max message limit
        crusher = message.message_create["sender_id"]
        crusher_crushes_count = session.query(Crush).filter(Crush.crusher == crusher).count()
        if crusher_crushes_count >= self.max_crusher_items:
            warnings.warn(f"user: {crusher} currently has no empty crush slot.")
            return None, []

        remaining_crusher_crushes = self.max_crusher_items - crusher_crushes_count

        message_data = message.message_create["message_data"]

        user_mentions = message_data["entities"]["user_mentions"]
        crushees = [{"id": item["id_str"], "screen_name": item["screen_name"]} for item in user_mentions]

        logger.debug(f"crusher: {crusher}, remaining: {remaining_crusher_crushes}")
        if remaining_crusher_crushes < len(crushees):
            warnings.warn(f"user: {crusher} does not have enough crush slots. Will skip some crushes")

        allowed_crushees = crushees[:remaining_crusher_crushes]
        self.register_crushes(crusher, allowed_crushees, message_id=message_id)
        return crusher, crushees

    def register_crushes(self, crusher: str, crushees: "list[dict[str,str]]", message_id: str = None) -> bool:
        breached_integrity = False
        with self.do_get_session() as session:
            for crushee in crushees:
                crush = Crush(
                    crusher=crusher,
                    crushee=crushee["id"],
                    crushee_screen_name=crushee["screen_name"],
                    message_id=message_id,
                )
                logger.debug(f"Register crush: {crusher} --> {crushee}")
                session.add(crush)
            try:
                session.commit()
            except exc.IntegrityError as err:
                # TODO: [pseudo] anonymise error data before logging it
                breached_integrity = True
                warnings.warn(str(err))
        return breached_integrity

    def update_matched_crushes(self) -> bool:
        found_new_crushes = False
        with self.do_get_session() as session:
            other: Crush = aliased(Crush)
            query_result: "list[Crush]" = (
                session.query(Crush)
                .join(
                    other,
                    (Crush.state == CrushState.PENDING)
                    & (other.crushee == Crush.crusher)
                    & (other.crusher == Crush.crushee),
                )
                .all()
            )
            for crush in query_result:
                crush.state = CrushState.MATCHED
                session.add(crush)
            session.commit()
            found_new_crushes = len(query_result) > 0
        return found_new_crushes

    def get_matched_crushes(self) -> "list[Crush]":

        query_result: "list[Crush]" = []
        with self.do_get_session() as session:
            query_result = session.query(Crush).filter(Crush.state == CrushState.MATCHED).all()

        return query_result

    def get_notified_crushes(self) -> "list[Crush]":

        query_result: "list[Crush]" = []
        with self.do_get_session() as session:
            query_result = session.query(Crush).filter(Crush.state == CrushState.NOTIFIED).all()

        return query_result

    def notify_crushes(self, crushes: "list[Crush]") -> "list[Crush]":
        for crush in crushes:
            # NOTE: we may skip the direct notification in case there are issues with the API rate
            message: DirectMessage = self.do_send_direct_message(
                recipient_id=crush.crusher,
                text=f"Hello,\n\n@{crush.crushee_screen_name} crushed you back! ^_^\nTime to slide into their DM.",
            )
            logger.debug(f"@{crush.crusher} Found your crush: {crush.crushee}")
            # The more atomic we are, the better it is, to avoid locking the DB while wating for the Twitter API rate limit lock
            with self.do_get_session() as session:
                crush = session.get(entity=Crush, ident=crush.id)
                crush.state = CrushState.NOTIFIED
                session.add(crush)
                session.commit()

            message.delete()
        return crushes

    def clean_up(self):
        """Delete all crushes in a notified state"""

        # TODO: delete messages older than the fixed constant (e.g. 30)
        with self.session_getter() as session:
            session.query(Crush).filter(Crush.state == CrushState.NOTIFIED).delete()
            session.commit()

    def fetch_and_register_crusher_crushees(self, count: int = GET_DIRECT_MESSAGES_MAX_COUNT):
        messages: "list[DirectMessage]" = self.do_get_direct_messages(count=count)
        for message in messages:
            recipient_id = message.message_create["target"]["recipient_id"]
            user_mentions = message.message_create["message_data"]["entities"]["user_mentions"]
            if recipient_id == self.twitter_bot_account_id and user_mentions:
                crusher, crushees = self.process_message(message)
                # delete the processed message if it containes at least one user mention to avoid having it listed again
                if crushees:
                    message.delete()

                # TODO: send acknowlegment
                # NOTE: due to low quota on the direct message endpoints, we avoid this step for now -> bot webpage!!!
                # notification_text = f"Registered your crushes: {[item['screen_name'] for item in crushees]}"
                # notification_message: DirectMessage = self.api.send_direct_message(crusher, notification_text)
                # notification_message.delete()


class Workflow:
    def __init__(
        self,
        bot: Bot = None,
    ) -> None:
        if bot is None:
            bot = Bot(api=get_api())
        self.bot = bot

    def run(self):
        self.bot.fetch_and_register_crusher_crushees()

        found_new_crushes = self.bot.update_matched_crushes()

        if found_new_crushes:
            matched_crushes = self.bot.get_matched_crushes()
            logger.debug(f"Matched crushes: {matched_crushes}")

            self.bot.notify_crushes(matched_crushes)

            notified_crushes = self.bot.get_notified_crushes()
            logger.debug(f"Notified crushes: {notified_crushes}")

            self.bot.clean_up()
