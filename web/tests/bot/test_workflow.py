import unittest
from unittest import mock
import datetime as dt
import re
import pickle

from tweepy.models import DirectMessage

from sqlalchemy.orm import sessionmaker
import sqlalchemy as db

from bot.models import Base, get_session, Crush, CrushState
from bot.cmb import get_session, get_api, Bot, Workflow


"""
Alice: -> Bob, Eve
Anna: -> Bob
Bob: -> Alice, Anna, Eve
Eve: -> Alice, Anna

# Crushes
{Alice, Bob}, {Alice, Eve}, {Anna, Bob}

# Remain messages:

"""

TEST_BOT_ACCOUNT_ID = "bot"
user_alice = {"id": "alice", "id_str": "alice", "screen_name": "alice_sn"}
user_anna = {"id": "anna", "id_str": "anna", "screen_name": "anna_sn"}
user_bob = {"id": "bob", "id_str": "bob", "screen_name": "bob_sn"}
user_eve = {"id": "eve", "id_str": "eve", "screen_name": "eve_sn"}
test_messages_json = [
    {
        "id": "alice->bob,eve",
        "message_create": {
            "target": {"recipient_id": TEST_BOT_ACCOUNT_ID},
            "sender_id": "alice",
            "message_data": {
                "text": "hi @bob, @eve",
                "entities": {
                    "user_mentions": [user_bob, user_eve],
                },
            },
        },
    },
    {
        "id": "anna->bob",
        "message_create": {
            "target": {"recipient_id": TEST_BOT_ACCOUNT_ID},
            "sender_id": "anna",
            "message_data": {
                "text": "hi @bob",
                "entities": {
                    "user_mentions": [user_bob],
                },
            },
        },
    },
    {
        "id": "bob->alice,anna,eve",
        "message_create": {
            "target": {"recipient_id": TEST_BOT_ACCOUNT_ID},
            "sender_id": "bob",
            "message_data": {
                "text": "hi @alice, @anna, @eve",
                "entities": {
                    "user_mentions": [user_alice, user_anna, user_eve],
                },
            },
        },
    },
    {
        "id": "eve->alice,anna",
        "message_create": {
            "target": {"recipient_id": TEST_BOT_ACCOUNT_ID},
            "sender_id": "eve",
            "message_data": {
                "text": "hi @alice, @anna",
                "entities": {
                    "user_mentions": [user_alice, user_anna],
                },
            },
        },
    },
]


class TestWorkflow(unittest.TestCase):
    ...

    def setUp(self) -> None:
        self.api = mock.MagicMock()
        self.engine = db.create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.session_maker = sessionmaker(self.engine)

    def test_run(self):
        api_mock = self.api
        api_mock.get_direct_messages.return_value = [
            DirectMessage.parse(api_mock, msg_json) for msg_json in test_messages_json
        ]
        core = Bot(api=api_mock, session_getter=self.session_maker, twitter_bot_account_id=TEST_BOT_ACCOUNT_ID)

        wkfl = Workflow(
            bot=core,
        )

        wkfl.run()

        api_mock.send_direct_message.assert_called()
        assert api_mock.send_direct_message.call_count == 3 * 2  # nb crushes matched x 2

    def test_process_message_skip_processed_messages(self):
        api_mock = self.api
        core = Bot(api=api_mock, session_getter=self.session_maker, twitter_bot_account_id=TEST_BOT_ACCOUNT_ID)
        msg1 = {
            "id": "1",
            "message_create": {
                "sender_id": "crusher1",
                "target": {"recipient_id": TEST_BOT_ACCOUNT_ID},
                "message_data": {
                    "entities": {
                        "user_mentions": [{"id": "crushee1", "id_str": "crushee1", "screen_name": "crushee1_sn"}]
                    }
                },
            },
        }
        msg2 = {
            "id": "2",
            "message_create": {
                "sender_id": "crusher2",
                "target": {"recipient_id": TEST_BOT_ACCOUNT_ID},
                "message_data": {
                    "entities": {
                        "user_mentions": [{"id": "crushee2", "id_str": "crushee2", "screen_name": "crushee2_sn"}]
                    }
                },
            },
        }
        messages_json = [msg1, msg2, msg1, msg2]
        direct_messages = [DirectMessage.parse(api_mock, msg_json) for msg_json in messages_json]

        with self.assertWarns(UserWarning) as context:
            for dm in direct_messages:
                core.process_message(message=dm)
        self.assertEqual(len(context.warnings), 2)

        for warning in context.warnings:
            self.assertRegex(
                text=str(warning.message),
                expected_regex=r"message with id: \d+ has already been processed by the system.",
                msg="Warning message isn't the expected one",
            )

        with core.do_get_session() as session:
            nb_items = session.query(Crush).count()
            self.assertEqual(nb_items, 2)

    def test_process_message_limit_max_crusher_items(self):
        api_mock = self.api
        core = Bot(
            api=api_mock,
            session_getter=self.session_maker,
            twitter_bot_account_id=TEST_BOT_ACCOUNT_ID,
            max_crusher_items=2,
        )
        msg1 = {
            "id": "1",
            "message_create": {
                "sender_id": "crusher1",
                "target": {"recipient_id": TEST_BOT_ACCOUNT_ID},
                "message_data": {"entities": {"user_mentions": [user_alice]}},
            },
        }
        msg2 = {
            "id": "2",
            "message_create": {
                "sender_id": "crusher1",
                "target": {"recipient_id": TEST_BOT_ACCOUNT_ID},
                "message_data": {"entities": {"user_mentions": [user_anna, user_bob, user_eve]}},
            },
        }
        msg3 = {
            "id": "3",
            "message_create": {
                "sender_id": "crusher1",
                "target": {"recipient_id": TEST_BOT_ACCOUNT_ID},
                "message_data": {"entities": {"user_mentions": [user_alice]}},
            },
        }
        msg4 = {
            "id": "4",
            "message_create": {
                "sender_id": "crusher2",
                "target": {"recipient_id": TEST_BOT_ACCOUNT_ID},
                "message_data": {"entities": {"user_mentions": [user_bob, user_eve, user_alice, user_anna]}},
            },
        }
        # Expected final state:
        # crusher1 -> user_alice, user_anna
        # crusher2 -> user_bob, user_eve

        messages_json = [msg1, msg2, msg3, msg4]
        direct_messages = [DirectMessage.parse(api_mock, msg_json) for msg_json in messages_json]

        with self.assertWarns(UserWarning) as context:
            for dm in direct_messages:
                core.process_message(message=dm)
        self.assertEqual(len(context.warnings), 3)

        warning_regexes = ["does not have enough", "has no empty", "does not have enough"]
        for idx, warning in enumerate(context.warnings):
            self.assertRegex(
                text=str(warning.message),
                expected_regex=warning_regexes[idx],
                msg="Warning message isn't the expected one",
            )
        with core.do_get_session() as session:
            nb_items = session.query(Crush).count()
            self.assertEqual(nb_items, 4)

    def test_clean_up(self):
        api_mock = self.api
        core = Bot(
            api=api_mock,
            session_getter=self.session_maker,
            twitter_bot_account_id=TEST_BOT_ACCOUNT_ID,
            max_crusher_items=2,
        )
        items = [
            {
                "crusher": "anna",
                "crushee": "alice",
                "crushee_screen_name": "alice",
                "message_id": "1",
                "created_on": dt.datetime(2022, 8, 7),
                "state": CrushState.NOTIFIED,
            },
            {
                "crusher": "alice",
                "crushee": "anna",
                "crushee_screen_name": "anna",
                "message_id": "2",
                "created_on": dt.datetime(2022, 9, 8),
                "state": CrushState.NOTIFIED,
            },
            {
                "crusher": "eve",
                "crushee": "bob",
                "crushee_screen_name": "bob",
                "message_id": "3",
                "created_on": dt.datetime(2022, 10, 11),
                "state": CrushState.READY,
            },
        ]
        with core.do_get_session() as session:
            for item in items:
                crush = Crush(
                    crusher=item["crusher"],
                    crushee=item["crushee"],
                    crushee_screen_name=item["crushee_screen_name"],
                    message_id=item["message_id"],
                    state=item["state"],
                    created_on=item["created_on"],
                )
                session.add(crush)
            session.commit()

        core.clean_up()

        with core.do_get_session() as session:
            nb_items = session.query(Crush).count()
            self.assertEqual(nb_items, 1, "Notified crushes should have been deleted from the DB")

    def test_notify_crushes(self):
        ...
        api_mock = self.api
        core = Bot(
            api=api_mock,
            session_getter=self.session_maker,
            twitter_bot_account_id=TEST_BOT_ACCOUNT_ID,
            max_crusher_items=2,
        )
        items = [
            {
                "crusher": "anna",
                "crushee": "alice",
                "crushee_screen_name": "alice",
                "message_id": "1",
                "created_on": dt.datetime(2022, 8, 7),
                "state": CrushState.MATCHED,
            },
            {
                "crusher": "alice",
                "crushee": "anna",
                "crushee_screen_name": "anna",
                "message_id": "2",
                "created_on": dt.datetime(2022, 9, 8),
                "state": CrushState.MATCHED,
            },
            {
                "crusher": "eve",
                "crushee": "bob",
                "crushee_screen_name": "bob",
                "message_id": "3",
                "created_on": dt.datetime(2022, 10, 11),
                "state": CrushState.READY,
            },
        ]

        with core.do_get_session() as session:
            for item in items:
                crush = Crush(
                    crusher=item["crusher"],
                    crushee=item["crushee"],
                    crushee_screen_name=item["crushee_screen_name"],
                    message_id=item["message_id"],
                    state=item["state"],
                    created_on=item["created_on"],
                )
                session.add(crush)
            session.commit()

        matched_crushes = core.get_matched_crushes()
        self.assertEqual(len(matched_crushes), 2)
        core.notify_crushes(matched_crushes)
        api_mock.send_direct_message.assert_called()
        notified_crushes = core.get_notified_crushes()
        self.assertEqual(len(notified_crushes), 2)

        with core.do_get_session() as session:
            nb_items = session.query(Crush).filter(Crush.state != CrushState.NOTIFIED).count()
            self.assertEqual(nb_items, 1, "Notified crushes should have been deleted from the DB")
