import json
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


# -- persistence --------------------------------------------------------------


def test_persist_and_reload(tmp_path):
    path = tmp_path / "jerry.json"
    store = ConversationStore(path=path)
    store.add("c1", "user", "remember this")
    store.add("c1", "assistant", "remembered")

    assert path.exists()
    # A fresh store on the same path recovers the history.
    reloaded = ConversationStore(path=path)
    assert reloaded.history("c1") == [
        {"role": "user", "content": "remember this"},
        {"role": "assistant", "content": "remembered"},
    ]


def test_no_path_does_not_write(tmp_path):
    path = tmp_path / "nope.json"
    store = ConversationStore()  # no path → pure in-memory
    store.add("c", "user", "hi")
    store.save()
    assert not path.exists()


def test_clear_persists(tmp_path):
    path = tmp_path / "m.json"
    store = ConversationStore(path=path)
    store.add("c", "user", "hi")
    store.clear("c")
    assert ConversationStore(path=path).history("c") == []


def test_corrupt_file_starts_empty(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{ this is not valid json", encoding="utf-8")
    store = ConversationStore(path=path)  # must not raise
    assert store.history("c") == []
    # And the store still works + repairs the file on the next write.
    store.add("c", "user", "ok now")
    assert json.loads(path.read_text(encoding="utf-8"))["conversations"]["c"]


def test_reload_respects_max_turns(tmp_path):
    path = tmp_path / "big.json"
    writer = ConversationStore(path=path)
    for i in range(10):
        writer.add("c", "user", f"m{i}")
    # A store with a smaller cap trims the loaded history to its most recent.
    reader = ConversationStore(max_turns=3, path=path)
    assert [t["content"] for t in reader.history("c")] == ["m7", "m8", "m9"]


# -- thread inheritance (history_for) -----------------------------------------


def test_history_for_merges_parent_then_thread():
    store = ConversationStore()
    store.add("chan", "user", "channel context")
    store.add("chan:123.45", "user", "thread reply")
    # Parent channel history comes first, then the thread's own turns.
    assert store.history_for(["chan", "chan:123.45"]) == [
        {"role": "user", "content": "channel context"},
        {"role": "user", "content": "thread reply"},
    ]


def test_history_for_dedupes_keys():
    store = ConversationStore()
    store.add("chan", "user", "once")
    assert store.history_for(["chan", "chan"]) == [{"role": "user", "content": "once"}]


def test_history_for_missing_keys_is_empty():
    store = ConversationStore()
    assert store.history_for(["a", "b"]) == []
