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
    Operation,
    bcp,
    chd,
    chm,
    compute_all,
    icp,
    ifn,
    load_edges_csv,
    load_partition_json,
    ned,
    ned_relative,
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


class TestSMUndirected:
    """CHGNN's metric.py treats the graph as UNDIRECTED and unweighted:
    reciprocal edges collapse to one pair, mu_k counts each intra pair
    TWICE (networkx subgraph edges * 2) while sigma_ij counts each cross
    pair ONCE. Validated against tools/chgnn/metric.py on the acme run.

    Tiny example, undirected pairs: AB, BC, DE, CD, EB.
    mu_0 = 2*2 = 4, mu_1 = 2*1 = 2, sigma_01 = 2.
    SM = 1/2 * (4/9 + 2/4) - 2/(2*3*2) = 17/36 - 1/6 = 11/36
    """

    def test_hand_computed_example(self):
        assert sm(PARTITION, EDGES, undirected=True) == pytest.approx(11 / 36)

    def test_reciprocal_edges_collapse(self):
        partition = {"A": 0, "B": 0}
        edges = [Edge("A", "B", "CALL", 1.0), Edge("B", "A", "CALL", 1.0)]
        # one undirected pair, mu = 2 -> SM = 2/4
        assert sm(partition, edges, undirected=True) == pytest.approx(0.5)


class TestNEDRelative:
    """CHGNN's NED variant: non-extreme means
    floor(avg*(1-eps)) <= size <= ceil(avg*(1+eps)), default eps=0.5."""

    def test_all_within_relative_bounds(self):
        # sizes 3,2: avg 2.5, eps 0.5 -> bounds [1, 4] -> all classes fine
        assert ned_relative(PARTITION) == pytest.approx(1.0)

    def test_tight_eps_all_extreme(self):
        # sizes 4,1: avg 2.5, eps 0.2 -> bounds [2, 3] -> all 5 extreme
        partition = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 1}
        assert ned_relative(partition, eps=0.2) == pytest.approx(0.0)


class TestCHGNNValidationGate:
    """VALIDATION GATE (CLAUDE.md): our implementation must reproduce
    tools/chgnn/metric.py exactly on the real acme run output.
    Expected values below were produced by running CHGNN's own
    get_structural_modularity / get_ned on this exact fixture."""

    @pytest.fixture
    def acme(self):
        import os
        path = os.path.join(os.path.dirname(__file__), "fixtures", "chgnn_acme_result.json")
        with open(path) as f:
            d = json.load(f)
        id2label = {n["id"]: n["label"] for n in d["nodes"]}
        partition = {
            id2label[nid]: ci
            for ci, c in enumerate(d["clusters"])
            for nid in c["nodes"]
        }
        edges = [
            Edge(id2label[r["id"].split("_")[0]], id2label[r["id"].split("_")[1]], "CALL", 1.0)
            for block in d["edges"]
            for r in block["relationship"]
        ]
        return partition, edges

    def test_sm_matches_chgnn(self, acme):
        partition, edges = acme
        assert sm(partition, edges, undirected=True) == pytest.approx(
            0.2015674603174603, abs=1e-12
        )

    def test_ned_matches_chgnn(self, acme):
        partition, _ = acme
        assert ned_relative(partition) == pytest.approx(
            0.5833333333333334, abs=1e-12
        )


class TestCHM:
    """CHM (Cohesion at Message level): per partition, mean pairwise
    f_msg over externally-invoked operations, where
    f_msg = (Jaccard(returns) + Jaccard(params)) / 2, normalized to [0,1].
    Partitions with fewer than 2 published operations score 1.0.

    Hand example: P0={A,B}, P1={C}. C calls A.f(int,String)->Product and
    B.g(int)->Product; nothing calls into P1.
      pair (f,g): J(par) = |{int}|/|{int,String}| = 1/2; J(ret) = 1/1 = 1
      f_msg = (0.5+1)/2 = 0.75 -> chm_0 = 0.75, chm_1 = 1.0, CHM = 0.875
    """

    PARTITION = {"A": 0, "B": 0, "C": 1}
    CALLS = [
        ("C", Operation("A", "f", ("int", "String"), "Product")),
        ("C", Operation("B", "g", ("int",), "Product")),
    ]

    def test_hand_computed_example(self):
        assert chm(self.PARTITION, self.CALLS) == pytest.approx(0.875)

    def test_internal_calls_do_not_publish_operations(self):
        calls = self.CALLS + [("A", Operation("B", "h", (), "void"))]
        # B.h is only called from inside P0 -> not part of the interface
        assert chm(self.PARTITION, calls) == pytest.approx(0.875)

    def test_identical_signatures_are_fully_cohesive(self):
        calls = [
            ("C", Operation("A", "f", ("int",), "Product")),
            ("C", Operation("B", "g", ("int",), "Product")),
        ]
        assert chm(self.PARTITION, calls) == pytest.approx(1.0)


class TestCHD:
    """CHD (Cohesion at Domain level): same aggregation, f_dom = Jaccard of
    domain terms (camelCase tokens of method name + non-JDK type names).

    Hand example: ops addProduct() and removeProduct() published by P0:
      terms {add,product} vs {remove,product} -> J = 1/3
      chd_0 = 1/3, chd_1 = 1.0, CHD = 2/3
    """

    PARTITION = {"A": 0, "B": 0, "C": 1}
    CALLS = [
        ("C", Operation("A", "addProduct", (), "void")),
        ("C", Operation("B", "removeProduct", (), "void")),
    ]

    def test_hand_computed_example(self):
        assert chd(self.PARTITION, self.CALLS) == pytest.approx(2 / 3)

    def test_domain_type_names_contribute_terms(self):
        calls = [
            ("C", Operation("A", "add", ("Product",), "void")),
            ("C", Operation("B", "remove", ("Product",), "void")),
        ]
        # terms {add,product} vs {remove,product} -> same 1/3 -> CHD = 2/3
        assert chd(self.PARTITION, calls) == pytest.approx(2 / 3)

    def test_jdk_types_are_not_domain_terms(self):
        calls = [
            ("C", Operation("A", "addProduct", ("String", "int"), "void")),
            ("C", Operation("B", "removeProduct", ("List",), "void")),
        ]
        assert chd(self.PARTITION, calls) == pytest.approx(2 / 3)


class TestBCP:
    """BCP: average over partitions of the entropy of a uniform distribution
    over the partition's use cases: bcp_i = ln(m_i), m_i = |union of use-case
    labels of member classes|. Lower is better.

    Hand example: P0 = {A:{UC1}, B:{UC1,UC2}} -> m_0 = 2 -> bcp_0 = ln 2.
    P1 = {C:{UC1}} -> m_1 = 1 -> bcp_1 = 0. BCP = ln(2)/2 ~ 0.34657
    """

    def test_hand_computed_example(self):
        import math
        partition = {"A": 0, "B": 0, "C": 1}
        usecases = {"A": {"UC1"}, "B": {"UC1", "UC2"}, "C": {"UC1"}}
        assert bcp(partition, usecases) == pytest.approx(math.log(2) / 2)

    def test_no_usecases_scores_zero(self):
        assert bcp({"A": 0}, {"A": set()}) == 0.0


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


class TestCHM_CHD_BCP:
    def test_chm_chd_hand_computed(self):
        from metrics.metrics import compute_chm_chd
        
        partition = {
            "A": 0, "B": 0, "C": 0,
            "D": 1, "E": 1
        }
        
        methods_by_class = {
            "B": [
                {"name": "m2", "returnType": "int", "parameters": ["java.lang.String"]},
                {"name": "m3", "returnType": "int", "parameters": ["int"]}
            ],
            "D": [
                {"name": "m4", "returnType": "void", "parameters": ["int"]}
            ]
        }
        
        method_calls = [
            {"srcClass": "D", "srcMethod": "unknown", "dstClass": "B", "dstMethod": "m2"},
            {"srcClass": "E", "srcMethod": "unknown", "dstClass": "B", "dstMethod": "m3"},
            {"srcClass": "C", "srcMethod": "unknown", "dstClass": "D", "dstMethod": "m4"}
        ]
        
        chm, chd = compute_chm_chd(partition, methods_by_class, method_calls)
        
        # Cluster 0 has O_0 = {(B, m2), (B, m3)}
        # f_msg(m2, m3) = 0.5 * (jaccard({'int'}, {'int'}) + jaccard({'java.lang.String'}, {'int'}))
        #               = 0.5 * (1.0 + 0.0) = 0.5. So chm_0 = 0.5.
        # Cluster 1 has O_1 = {(D, m4)}. Since |O_1| = 1, chm_1 = 1.0.
        # Average CHM = (0.5 + 1.0) / 2 = 0.75
        assert chm == pytest.approx(0.75)
        
        # For CHD:
        # terms(m2) = {'m2'} (java, lang, string, int filtered out)
        # terms(m3) = {'m3'}
        # jaccard({'m2'}, {'m3'}) = 0.0. So chd_0 = 0.0.
        # chd_1 = 1.0.
        # Average CHD = (0.0 + 1.0) / 2 = 0.5
        assert chd == pytest.approx(0.5)

    def test_bcp_hand_computed(self):
        from metrics.metrics import compute_bcp
        
        partition = {
            "AController": 0, "B": 0, "CController": 0,
            "D": 1, "E": 1
        }
        
        edges = [
            Edge("AController", "B", "CALL"),
            Edge("B", "CController", "CALL"),
            Edge("D", "E", "CALL"),
            Edge("CController", "D", "CALL"),
            Edge("E", "B", "CALL")
        ]
        
        # Reachable from AController: AController, B, CController, D, E
        # Reachable from CController: CController, D, E, B
        # Use cases for classes:
        # AController: {AController}
        # B: {AController, CController}
        # CController: {AController, CController}
        # D: {AController, CController}
        # E: {AController, CController}
        #
        # Cluster 0 (AController, B, CController) use cases: {AController, CController} -> m_0 = 2 -> bcp_uni_0 = log2(2) = 1.0
        # Counts in Cluster 0: AController (3 times reached), CController (2 times reached) -> total 5
        # Entropy: -0.6 * log2(0.6) - 0.4 * log2(0.4) = 0.97095
        #
        # Cluster 1 (D, E) use cases: {AController, CController} -> m_1 = 2 -> bcp_uni_1 = log2(2) = 1.0
        # Counts in Cluster 1: AController (2 times reached), CController (2 times reached) -> total 4 -> p = 0.5, 0.5
        # Entropy: 1.0
        #
        # Averages: uniform = 1.0, entropy = 0.985475
        uni, ent = compute_bcp(partition, edges)
        assert uni == pytest.approx(1.0)
        assert ent == pytest.approx(0.9854753, abs=1e-6)

