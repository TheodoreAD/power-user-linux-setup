"""pip install blinker

The same signal/observer library Flask itself uses internally. Fans out to multiple in-process
subscribers, zero ceremony, no server.
"""

from blinker import Signal

item_created: Signal = Signal()


def test_signal_calls_connected_receivers() -> None:
    received: list[tuple[str, dict[str, object]]] = []

    def on_item_created(sender: str, **kwargs: object) -> None:
        received.append((sender, kwargs))

    item_created.connect(on_item_created)
    item_created.send("app", item_id=1)
    assert received == [("app", {"item_id": 1})]
