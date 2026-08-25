"""Goal 4 -- real-world research distillation, five-stage pipeline tests."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest

from scheduler.research import (
    BM25, Doc, citation_rank, content_tokens, distill,
    extract_key_sentences, proximity_ok, rocchio_query,
)


def test_bm25_ranks_term_rich_doc_higher():
    docs = [
        Doc(id="a", text="Rust ownership borrowing lifetimes borrow checker.", title="A"),
        Doc(id="b", text="Baking sourdough bread with warm water and salt.", title="B"),
    ]
    bm = BM25(docs)
    scores = bm.scores(content_tokens("borrow checker ownership"))
    assert scores[0] > scores[1], "doc with the query terms must score higher"
    assert scores[0] > 0


def test_proximity_filters_far_apart_terms():
    near = Doc(id="n", text="the bus and the miner ride together daily",
               title="n")
    far = Doc(id="f", text="the bus is large and very wide for the whole street, "
                           "and later a far away miner rests at the distant end of town",
              title="f")
    # "bus" and "miner" co-occur within a small window in `near`, not in `far`.
    assert proximity_ok(near, ["bus", "miner"], window=8) is True
    assert proximity_ok(far, ["bus", "miner"], window=8) is False


def test_citation_rank_authoritative_doc_top():
    docs = [
        Doc(id="survey", text="x", title="survey", citations=["primary", "primary"]),
        Doc(id="primary", text="y", title="primary", citations=["foundational"]),
        Doc(id="foundational", text="z", title="foundational", citations=[]),
    ]
    rank = citation_rank(docs)
    by_id = dict(zip([d.id for d in docs], rank))
    # "foundational" is cited by everyone reachable, so it accumulates the most mass.
    assert by_id["foundational"] > by_id["survey"]


def test_rocchio_adds_new_discriminative_term():
    query = content_tokens("solar")
    top = [
        Doc(id="1", text="solar panels convert sunlight. panels efficiency panels cost panels panels", title="1"),
        Doc(id="2", text="solar cells also convert sunlight to electricity efficiently", title="2"),
    ]
    expanded = rocchio_query(query, top, n_terms=3)
    assert "solar" in expanded
    extra = [t for t in expanded if t not in query]
    assert len(extra) <= 3
    # a topical repeated term (efficiency/cells) should be a plausible expansion
    assert any(t in ("efficiency", "cells") for t in extra)


def test_extract_key_sentences_prefers_cue_sentences():
    d = Doc(id="d", title="Study", text=(
        "Introduction to the problem. We found that the new method cuts latency by half. "
        "Some background details here. In conclusion we demonstrate the result clearly."
    ))
    keys = extract_key_sentences(d, max_sentences=2)
    assert any("cuts latency" in k for k in keys)
    assert any("demonstrate" in k for k in keys)


def test_extract_penalizes_boilerplate():
    d = Doc(id="d2", title="X", text="Please click here to subscribe. This is the key finding we found.")
    keys = extract_key_sentences(d, max_sentences=1)
    assert "we found" in keys[0]
    assert "click" not in keys[0]


def test_distill_end_to_end_ranks_and_extracts():
    docs = [
        {"id": "1", "title": "A survey", "text": (
            "we review the caffeine adenosine receptor. we found that the caffeine "
            "dose boosts the receptor a lot."), "citations": ["2", "3"]},
        {"id": "2", "title": "Primary", "text": (
            "caffeine activates the adenosine receptor here and the results show "
            "the wakefulness clearly."), "citations": ["3"]},
        {"id": "3", "title": "Foundational", "text": (
            "the adenosine receptor binds caffeine, and we conclude the evidence "
            "demonstrates the mechanism clearly."), "citations": []},
    ]
    rep = distill("caffeine adenosine receptor", documents=docs)
    assert rep.included_docs == len(docs)
    assert rep.ranked, "distill must return at least one ranked doc"
    scores = [d["score"] for d in rep.ranked]
    assert scores == sorted(scores, reverse=True), "ranked must be desc by score"
    # every ranked doc should carry structural extraction
    for d in rep.ranked:
        assert "top_sentences" in d
    assert isinstance(rep.feedback_added, list)
