"""Crew directory: every agent's prompt must carry the full roster."""

from pathlib import Path

from clawcrew.config import load_config

APPROVED = {
    "jerry": "",
    "elaine": "jerry",
    "whatley": "jerry",
    "frank": "jerry",
    "leo": "jerry",
    "jackie": "jerry",
    "lloyd": "jerry",
    "davola": "jerry",
    "bania": "elaine",
    "peterman": "elaine",
    "george": "whatley",
    "kramer": "whatley",
    "morty": "whatley",
    "newman": "whatley",
    "soupnazi": "whatley",
    "mickey": "whatley",
    "babu": "whatley",
    "puddy": "frank",
    "bookman": "frank",
}


def test_roster_matches_approved_org():
    crew = load_config()
    assert len(crew.agents) == 19
    assert {a.handle: a.reports_to for a in crew.agents} == APPROVED


def test_every_prompt_contains_full_directory_and_self_marker():
    crew = load_config()
    for agent in crew.agents:
        p = crew.system_prompt_for(agent)
        for other in crew.agents:
            assert f"@{other.handle}" in p, f"{other.handle} missing from {agent.handle}'s prompt"
        assert p.count("(you)") == 1
        assert "Never invent or guess a handle" in p


def test_reports_to_renders_in_directory():
    crew = load_config()
    jerry = next(a for a in crew.agents if a.handle == "jerry")
    p = crew.system_prompt_for(jerry)
    assert "reports to @jerry" in p
    assert "reports to @whatley" in p
    assert "reports to @elaine" in p
    assert "reports to @frank" in p


def test_id_map_renders_slack_ids():
    crew = load_config()
    jerry = next(a for a in crew.agents if a.handle == "jerry")
    p = crew.system_prompt_for(jerry, id_map={"kramer": "U123"})
    assert "<@U123> (@kramer)" in p


def test_crew_directory_placeholder(tmp_path: Path):
    roster = tmp_path / "roster.yaml"
    roster.write_text(
        "crew:\n"
        "  name: T\n"
        "defaults:\n"
        "  system_prompt: |\n"
        "    Intro {name}.\n"
        "    {crew_directory}\n"
        "    Outro.\n"
        "agents:\n"
        "  - { name: A, handle: a, role: X }\n"
        "  - { name: B, handle: b, role: Y, reports_to: a }\n"
    )
    crew = load_config(roster)
    p = crew.system_prompt_for(crew.agents[0])
    assert "Intro A." in p and "Outro." in p
    assert p.index("@b") < p.index("Outro.")
    assert "reports to @a" in p
