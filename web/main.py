from bot.cmb import *

if __name__ == "__main__":

    recreate_all()

    core = Core(None)
    core.register_crushes("alice", [{"id": "bob", "screen_name": "bob"}, {"id": "eve", "screen_name": "eve"}])
    core.register_crushes("eve", [{"id": "alice", "screen_name": "alice"}, {"id": "anna", "screen_name": "anna"}])
    core.register_crushes("anna", [{"id": "bob", "screen_name": "bob"}])
    core.register_crushes(
        "bob",
        [
            {"id": "alice", "screen_name": "alice"},
            {"id": "anna", "screen_name": "anna"},
            {"id": "eve", "screen_name": "eve"},
        ],
    )
