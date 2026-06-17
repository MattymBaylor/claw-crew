from clawcrew.provision import ChannelInfo, channels_to_join


def _channels():
    return [
        ChannelInfo(id="C1", name="general", is_member=False),
        ChannelInfo(id="C2", name="resources", is_member=False),
        ChannelInfo(id="C3", name="huddle", is_member=True),  # already in
        ChannelInfo(id="C4", name="owner-office", is_member=False),
    ]


def test_joins_all_public_except_office():
    targets = channels_to_join(
        _channels(),
        office_channel="owner-office",
        allow_office_access=False,
        required_channels=("resources", "huddle"),
        join_all_public_channels=True,
    )
    names = {c.name for c in targets}
    assert names == {"general", "resources"}  # office excluded, huddle already member


def test_office_included_when_allowed():
    targets = channels_to_join(
        _channels(),
        office_channel="owner-office",
        allow_office_access=True,
        required_channels=(),
        join_all_public_channels=True,
    )
    assert "owner-office" in {c.name for c in targets}


def test_required_only_when_not_joining_all():
    targets = channels_to_join(
        _channels(),
        office_channel="owner-office",
        allow_office_access=False,
        required_channels=("resources", "huddle"),
        join_all_public_channels=False,
    )
    # only required channels we are not already in -> resources
    assert {c.name for c in targets} == {"resources"}


def test_required_office_overrides_exclusion():
    chans = [ChannelInfo(id="C4", name="owner-office", is_member=False)]
    targets = channels_to_join(
        chans,
        office_channel="owner-office",
        allow_office_access=False,
        required_channels=("owner-office",),
        join_all_public_channels=False,
    )
    assert {c.name for c in targets} == {"owner-office"}
