import threading

from clawcrew.memory import DEFAULT_MAX_TURNS, ConversationStore


def test_add_and_history_order():
    store = ConversationStore()
    store.add("c1", "user", "hello")
    store.add("c1", "assistant", "hi there")
    store.add("c1", "user", "how are you")

    assert store.history("c1") == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
        {"role": "user", "content": "how are you"},
    ]


def test_history_unknown_key_is_empty():
    store = ConversationStore()
    assert store.history("nope") == []


def test_keys_are_isolated():
    store = ConversationStore()
    store.add("a", "user", "from a")
    store.add("b", "user", "from b")

    assert store.history("a") == [{"role": "user", "content": "from a"}]
    assert store.history("b") == [{"role": "user", "content": "from b"}]


def test_default_max_turns():
    store = ConversationStore()
    assert store.max_turns == DEFAULT_MAX_TURNS


def test_trim_keeps_most_recent():
    store = ConversationStore(max_turns=3)
    for i in range(6):
        store.add("c", "user", f"m{i}")

    history = store.history("c")
    assert len(history) == 3
    assert [t["content"] for t in history] == ["m3", "m4", "m5"]


def test_history_returns_copy():
    store = ConversationStore()
    store.add("c", "user", "original")

    snapshot = store.history("c")
    snapshot[0]["content"] = "mutated"
    snapshot.append({"role": "assistant", "content": "extra"})

    # Mutating the returned list/dicts must not affect the store.
    assert store.history("c") == [{"role": "user", "content": "original"}]


def test_clear():
    store = ConversationStore()
    store.add("c", "user", "hello")
    store.clear("c")
    assert store.history("c") == []
    # Clearing an unknown key is a no-op.
    store.clear("never-seen")


def test_invalid_max_turns_raises():
    import pytest

    with pytest.raises(ValueError):
        ConversationStore(max_turns=0)


def test_concurrent_adds_are_safe():
    store = ConversationStore(max_turns=10_000)
    threads = [
        threading.Thread(
            target=lambda n=n: [store.add("c", "user", f"{n}-{i}") for i in range(200)]
        )
        for n in range(8)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # No lost updates: every add landed exactly once.
    assert len(store.history("c")) == 8 * 200
