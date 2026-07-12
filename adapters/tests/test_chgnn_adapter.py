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

    def test_inheritance_also_counts_as_usage(self):
        # CHGNN's own acme data lists every EXTENDS/IMPLEMENTS target in the
        # usage counts too (verified 10/10); pure-inheritance parents with a
        # zero usage row make the GCN produce NaNs (zero struct degree).
        icu = build_icu(NODES, EDGES)
        assert icu["B"]["usedClassesToCount"] == {"C": 1, "A": 1}
        assert icu["A"]["usedByClassesToCount"] == {"B": 1}

    def test_superclass_and_interfaces(self):
        icu = build_icu(NODES, EDGES)
        assert icu["B"]["superClass"] == "A"
        assert icu["A"]["superClass"] == "java.lang.Object"
        assert icu["A"]["implementedInterfaces"] == []

    def test_every_node_present_even_if_isolated(self):
        icu = build_icu(NODES + ["Z"], EDGES)
        assert icu["Z"]["usedClassesToCount"] == {}


class TestCallgraph:
    def test_reachable_follows_call_and_field_edges(self):
        # FIELD edges are DI wiring (Spring injects, then dispatches) so they
        # carry reachability; EXTENDS does not (B->A must not be followed).
        assert reachable(EDGES, "D") == {"D", "E", "B", "C"}
        # from A: A->B CALL, A->C FIELD, then C->D->E
        assert reachable(EDGES, "A") == {"A", "B", "C", "D", "E"}
        # a pure FIELD link carries reachability on its own
        assert reachable([("X", "Y", "FIELD", 1)], "X") == {"X", "Y"}
        # EXTENDS alone does not
        assert reachable([("X", "Y", "EXTENDS", 1)], "X") == {"X"}

    def test_dot_annotates_reachable_call_edges_per_entrypoint(self):
        dot = build_callgraph_dot(NODES, EDGES, ["E"])
        ep = "{type: web, method: GET, uri: [/E], entry: E, entrydisplayname: E.call}"
        assert f'"E.call" -> "[{ep}] E.call"' in dot
        assert f'"[{ep}] B.call" -> "[{ep}] C.call"' in dot
        # A is not reachable from E: its edges must not carry E's annotation
        assert f'"[{ep}] A.call"' not in dot

    def test_dot_includes_field_edges_as_links(self):
        # A -> C is FIELD: within A's reachable set it must appear as a link
        dot = build_callgraph_dot(NODES, EDGES, ["A"])
        ep = "{type: web, method: GET, uri: [/A], entry: A, entrydisplayname: A.call}"
        assert f'"[{ep}] A.call" -> "[{ep}] C.call"' in dot

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
