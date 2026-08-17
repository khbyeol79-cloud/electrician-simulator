from app.services.wiring_network_service import build_network_components, compare_networks


def test_free_junction_numbers_do_not_change_network_signature():
    roles = {
        "PB0-2": "external", "MC1-4": "functional",
        "TB5-06": "free_junction", "TB5-07": "free_junction",
        "TB5-13": "free_junction", "TB5-14": "free_junction",
    }
    first = build_network_components(
        [("PB0-2", "TB5-06"), ("TB5-06", "TB5-07"), ("TB5-07", "MC1-4")], roles
    )
    second = build_network_components(
        [("PB0-2", "TB5-13"), ("TB5-13", "TB5-14"), ("TB5-14", "MC1-4")], roles
    )
    assert first[0].signature == second[0].signature == frozenset({"PB0-2", "MC1-4"})


def test_network_comparison_reports_merge_unused_junction_and_loop():
    roles = {"A": "functional", "B": "functional", "C": "functional", "D": "functional",
             "T1": "free_junction", "T2": "free_junction", "T3": "free_junction"}
    components = build_network_components(
        [("A", "T1"), ("T1", "B"), ("B", "C"), ("T2", "T3"), ("T3", "T2")], roles
    )
    result = compare_networks(components, {"N1": frozenset({"A", "B"}), "N2": frozenset({"C", "D"})})
    assert result.merged_component_count == 1
    assert result.isolated_junction_count == 1
    assert result.loop_count == 1
    assert not result.electrically_equivalent

