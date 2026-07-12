"""Tests for the CHGNN adapter using the same tiny 5-class graph as the
metrics tests: A,B,C call/extend each other; E is a web entrypoint.

Graph (src, dst, type, weight):
    A -> B  CALL 2      B -> C CALL 1      C -> D CALL 1
    D -> E  CALL 1      E -> B CALL 2
    B -> A  EXTENDS 1   C -> I IMPLEMENTS 1 (I not a node -> ignored)
    A -> C  FIELD 1
"""

import json

import pytest

from adapters.chgnn_adapter import (
    build_callgraph_dot,
    build_db_json,
    build_icu,
    build_service_json,
    reachable,
)

NODES = ["A", "B", "C", "D", "E"]
EDGES = [
    ("A", "B", "CALL", 2),
    ("B", "C", "CALL", 1),
    ("C", "D", "CALL", 1),
    ("D", "E", "CALL", 1),
    ("E", "B", "CALL", 2),
    ("B", "A", "EXTENDS", 1),
    ("A", "C", "FIELD", 1),
]


class TestICU:
    def test_used_counts_aggregate_call_and_field(self):
        icu = build_icu(NODES, EDGES)
        assert icu["A"]["usedClassesToCount"] == {"B": 2, "C": 1}
        assert icu["B"]["usedByClassesToCount"] == {"A": 2, "E": 2}

    def test_superclass_and_interfaces(self):
        icu = build_icu(NODES, EDGES)
        assert icu["B"]["superClass"] == "A"
        assert icu["A"]["superClass"] == "java.lang.Object"
        assert icu["A"]["implementedInterfaces"] == []

    def test_every_node_present_even_if_isolated(self):
        icu = build_icu(NODES + ["Z"], EDGES)
        assert icu["Z"]["usedClassesToCount"] == {}


class TestCallgraph:
    def test_reachable_follows_call_edges_only(self):
        # from E: E->B->C->D->(E). EXTENDS/FIELD must not extend the set.
        assert reachable(EDGES, "E") == {"E", "B", "C", "D"}

    def test_dot_annotates_reachable_call_edges_per_entrypoint(self):
        dot = build_callgraph_dot(NODES, EDGES, ["E"])
        ep = "{type: web, method: GET, uri: [/E], entry: E, entrydisplayname: E.call}"
        assert f'"E.call" -> "[{ep}] E.call"' in dot
        assert f'"[{ep}] B.call" -> "[{ep}] C.call"' in dot
        # A is not reachable from E: its edges must not carry E's annotation
        assert f'"[{ep}] A.call"' not in dot

    def test_service_json_matches_dot_annotation(self):
        service = build_service_json(["E"])
        assert service == [{
            "service_entry_name":
                "{type: web, method: GET, uri: [/E], entry: E, entrydisplayname: E.call}",
            "class_method_name": ["E.call"],
        }]


class TestDbJson:
    def test_expands_crud_letters(self):
        db = build_db_json({"B": {"account": "RU"}})
        assert {"service_name": "B.call", "db_name": "account", "crud": "R"} in db
        assert {"service_name": "B.call", "db_name": "account", "crud": "U"} in db
        assert len(db) == 2
