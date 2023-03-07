# Crush-me-back bot
from re import match
import warnings
from sqlalchemy import exc
import tweepy
from tweepy.models import DirectMessage
from sqlalchemy.orm import aliased

from .config import TWITTER_BOT_ACCOUNT_ID, get_api

api = get_api()

from .models import Crush, CrushState, get_session, recreate_all


"""
Alice: -> Bob, Eve
Anna: -> Bob
Bob: -> Alice, Anna, Eve
Eve: -> Alice, Anna

# Crushes
{Alice, Bob}, {Alice, Eve}, {Anna, Bob}

## Flow:
on new messages:

ready -> matched ->
- register crushes
- [delete] crush messages
- collect matching crushes
- notify matching crushes
- [delete] crush notification messages
- cleanup database
"""


class Core(object):
    def __init__(self, api: tweepy.API, *args, **kwargs):
        self.api = api

    def register_crushes(self, crusher: str, crushees: "list[dict[str,str]]", message_id: str = None):
        with get_session() as session:
            for crushee in crushees:
                crush = Crush(
                    crusher=crusher,
                    crushee=crushee["id"],
                    crushee_screen_name=crushee["screen_name"],
                    message_id=message_id,
                )
                print("Register crush: ", crusher, "-->", crushee)
                session.add(crush)
            try:
                session.commit()
            except exc.IntegrityError as err:
                # TODO: [pseudo] anonymise error data before logging it
                warnings.warn(str(err))
        # found_new_crushes = self.update_matched_crushes()
        # return found_new_crushes

    def update_matched_crushes(self) -> bool:
        found_new_crushes = False
        with get_session() as session:
            other: Crush = aliased(Crush)
            query_result: "list[Crush]" = (
                session.query(Crush)
                .join(
                    other,
                    (Crush.state == CrushState.READY)
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
        with get_session() as session:
            query_result = session.query(Crush).filter(Crush.state == CrushState.MATCHED).all()
        return query_result

    def get_notified_crushes(self) -> "list[Crush]":

        query_result: "list[Crush]" = []
        with get_session() as session:
            query_result = session.query(Crush).filter(Crush.state == CrushState.NOTIFIED).all()

        return query_result

    def notify_crushes(self, crushes: "list[Crush]") -> "list[Crush]":
        for crush in crushes:
            # NOTE: getting as atomic as possible
            with get_session() as session:
                # TODO: send Twitter direct message notification!
                message: DirectMessage = self.api.send_direct_message(
                    recipient_id=crush.crusher,
                    text=f"Hello, @{crush.crushee_screen_name} crushed you back! ^_^\nTime to slide into their DM.",
                )
                print(f"@{crush.crusher} Found your crush: {crush.crushee}")
                crush.state = CrushState.NOTIFIED
                session.add(crush)
                session.commit()
                # NOTE: For now, let's reduce the amount of API call >_<
                # message.delete()
        return crushes

    def clean_up(self, crushes: "list[Crush]"):
        for crush in crushes:
            print("cleaned-up crush: ", crush)

        with get_session() as session:
            query_result = session.query(Crush).filter(Crush.state == CrushState.NOTIFIED).delete()
            session.commit()


# class Bot:
#     def __init__(self, *args, **kwargs):
#         ...

#     def process_message(self, message: DirectMessage) -> "tuple[str,list[str]]":
#         ...
#         message_data = message.message_create["message_data"]
#         user_mentions = message_data["entities"]["user_mentions"]
#         crusher = message.message_create["sender_id"]
#         crushees = [item["id_str"] for item in user_mentions]
#         return crusher, crushees


class Workflow:
    def __init__(self) -> None:
        self.api = get_api()
        self.core = Core(api=self.api)

    def process_message(self, message: DirectMessage) -> "tuple[str,list[str]]":
        message_data = message.message_create["message_data"]
        print("message", message)
        print("message_data: ", message_data)
        user_mentions = message_data["entities"]["user_mentions"]
        crusher = message.message_create["sender_id"]
        crushees = [{"id": item["id_str"], "screen_name": item["screen_name"]} for item in user_mentions]
        self.core.register_crushes(crusher, crushees)
        return crusher, crushees

    def fetch_and_register_crusher_crushees(self, count: int = 128):
        messages: "list[DirectMessage]" = self.api.get_direct_messages(count=count)
        for message in messages:
            recipient_id = message.message_create["target"]["recipient_id"]
            user_mentions = message.message_create["message_data"]["entities"]["user_mentions"]
            if recipient_id == TWITTER_BOT_ACCOUNT_ID and user_mentions:
                crusher, crushees = self.process_message(message)
                # TODO: send acknowlegment
                # NOTE: due to low quota on the direct message endpoints, we avoid this step!!!
                # notification_text = f"Registered your crushes: {[item['screen_name'] for item in crushees]}"
                # notification_message: DirectMessage = self.api.send_direct_message(crusher, notification_text)
                # message.delete()
                # notification_message.delete()

    def run(self):
        self.fetch_and_register_crusher_crushees()

        found_new_crushes = self.core.update_matched_crushes()

        if found_new_crushes:
            matched_crushes = self.core.get_matched_crushes()
            print("Matched crushes: ", matched_crushes)

            notified_crushes = self.core.notify_crushes(matched_crushes)

            self.core.clean_up(matched_crushes)


"""
send_direct_message(recipient_id, text, *, quick_reply_options=None, attachment_type=None, attachment_media_id=None, ctas=None, **kwargs) method of tweepy.api.API instance
    send_direct_message(recipient_id, text, *, quick_reply_options,    
    """
