"""Unit tests for the metrics module, using a tiny hand-computed example.

Example graph (5 classes, 2 partitions), all edges type CALL:

    Partition 0 = {A, B, C}
    Partition 1 = {D, E}

    Edges (src, dst, type, weight):
        A -> B  CALL  2   (inside P0)
        B -> C  CALL  1   (inside P0)
        D -> E  CALL  1   (inside P1)
        C -> D  CALL  1   (P0 -> P1, crossing)
        E -> B  CALL  2   (P1 -> P0, crossing)

Hand computations (Jin et al., TSE 2021 formulations):

SM:  edge COUNTS (unweighted). mu_0 = 2 (A->B, B->C), N_0 = 3;
     mu_1 = 1 (D->E), N_1 = 2; sigma_{0,1} = 2 (C->D, E->B).
     SM = (1/2)(2/9 + 1/4) - (1/1) * 2/(2*3*2)
        = 0.2361111... - 0.1666666... = 0.0694444...

ICP: weighted, CALL edges only. crossing weight = 1 + 2 = 3;
     total call weight = 2+1+1+1+2 = 7.  ICP = 3/7 = 0.4285714...

IFN: interfaces(P0) = {B} (called by E from outside);
     interfaces(P1) = {D} (called by C from outside).
     IFN = (1 + 1)/2 = 1.0

NED: with standard bounds 5 <= size <= 20 both partitions (sizes 3, 2)
     are extreme -> NED = 1 - 5/5 = 0.0.
     With bounds [3, 20]: P0 (size 3) non-extreme, P1 (size 2) extreme
     -> NED = 1 - 2/5 = 0.6.
"""

import pytest

import json

from metrics.metrics import (
    Edge,
    compute_all,
    icp,
    ifn,
    load_edges_csv,
    load_partition_json,
    ned,
    sm,
)

PARTITION = {"A": 0, "B": 0, "C": 0, "D": 1, "E": 1}

EDGES = [
    Edge("A", "B", "CALL", 2.0),
    Edge("B", "C", "CALL", 1.0),
    Edge("D", "E", "CALL", 1.0),
    Edge("C", "D", "CALL", 1.0),
    Edge("E", "B", "CALL", 2.0),
]


class TestSM:
    def test_hand_computed_example(self):
        assert sm(PARTITION, EDGES) == pytest.approx(0.0694444444, abs=1e-9)

    def test_single_partition_has_no_inter_term(self):
        partition = {"A": 0, "B": 0}
        edges = [Edge("A", "B", "CALL", 1.0)]
        # SM = (1/1) * (1/4) - 0
        assert sm(partition, edges) == pytest.approx(0.25)


class TestICP:
    def test_hand_computed_example(self):
        assert icp(PARTITION, EDGES) == pytest.approx(3 / 7)

    def test_ignores_non_call_edges(self):
        edges = EDGES + [Edge("A", "D", "EXTENDS", 100.0)]
        assert icp(PARTITION, edges) == pytest.approx(3 / 7)

    def test_no_call_edges_returns_zero(self):
        assert icp(PARTITION, [Edge("A", "D", "EXTENDS", 1.0)]) == 0.0


class TestIFN:
    def test_hand_computed_example(self):
        assert ifn(PARTITION, EDGES) == pytest.approx(1.0)

    def test_class_called_twice_from_outside_counted_once(self):
        # B receives calls from both D and E (outside P0): still ONE interface.
        edges = EDGES + [Edge("D", "B", "CALL", 1.0)]
        assert ifn(PARTITION, edges) == pytest.approx(1.0)

    def test_only_call_edges_create_interfaces(self):
        # An EXTENDS edge crossing partitions does not make an interface.
        edges = [Edge("A", "D", "EXTENDS", 1.0)]
        assert ifn(PARTITION, edges) == 0.0


class TestNED:
    def test_default_bounds_both_partitions_extreme(self):
        # sizes 3 and 2, default bounds [5, 20]: all 5 classes extreme.
        assert ned(PARTITION) == pytest.approx(0.0)

    def test_bounds_3_20(self):
        # P0 (size 3) non-extreme, P1 (size 2) extreme: 1 - 2/5 = 0.6
        assert ned(PARTITION, lo=3, hi=20) == pytest.approx(0.6)

    def test_bounds_2_20_all_non_extreme(self):
        assert ned(PARTITION, lo=2, hi=20) == pytest.approx(1.0)

    def test_upper_bound(self):
        # one partition of 6 classes with hi=5 -> all extreme.
        partition = {f"C{i}": 0 for i in range(6)}
        assert ned(partition, lo=1, hi=5) == pytest.approx(0.0)


class TestFileIO:
    @pytest.fixture
    def files(self, tmp_path):
        partition_file = tmp_path / "partition.json"
        partition_file.write_text(json.dumps(PARTITION))
        edges_file = tmp_path / "edges.csv"
        edges_file.write_text(
            "src,dst,type,weight\n"
            "A,B,CALL,2\n"
            "B,C,CALL,1\n"
            "D,E,CALL,1\n"
            "C,D,CALL,1\n"
            "E,B,CALL,2\n"
        )
        return partition_file, edges_file

    def test_load_partition_json(self, files):
        assert load_partition_json(files[0]) == PARTITION

    def test_load_edges_csv(self, files):
        assert load_edges_csv(files[1]) == EDGES

    def test_compute_all(self, files):
        result = compute_all(load_partition_json(files[0]), load_edges_csv(files[1]))
        assert result["SM"] == pytest.approx(0.0694444444, abs=1e-9)
        assert result["ICP"] == pytest.approx(3 / 7)
        assert result["IFN"] == pytest.approx(1.0)
        assert result["NED"] == pytest.approx(0.0)
