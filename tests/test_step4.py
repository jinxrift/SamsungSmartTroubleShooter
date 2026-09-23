import json

from src.match_deeplink import (
    build_bm25_index,
    build_dense_index,
    match_deeplink_for_text,
    merge_and_rerank,
)


def test_indexes_are_built_for_catalog_text():
    bm25 = build_bm25_index()
    dense = build_dense_index()

    assert len(bm25["docs"]) > 0
    assert len(dense["docs"]) == len(bm25["docs"])
    assert "bixby://dummy_positive" in {entry["deeplink"] for entry in bm25["docs"]}


def test_match_prefers_specific_screen_over_parent_menu():
    result = match_deeplink_for_text("switch time format to 24 hour display")
    assert result["message"] == "Switch Time Format"
    assert result["deeplink"].startswith("bixby://masked/act/")


def test_adversarial_no_match_falls_back_to_dummy_positive():
    result = match_deeplink_for_text("mystic orbital moon telemetry dashboard")
    assert result["deeplink"] == "bixby://dummy_positive"


def test_merged_candidates_are_reranked_by_specificity():
    bm25 = build_bm25_index()
    dense = build_dense_index()
    merged = merge_and_rerank(
        "disable mouse keys accessibility",
        bm25["docs"],
        dense["docs"],
        top_k=5,
    )
    assert merged["best"]["message"] in {"Disable Mouse Keys", "Enable Mouse Keys"}
    assert merged["best"]["deeplink"].startswith("bixby://masked/act/")
