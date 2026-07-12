package com.fyp.extractor;

import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;

/**
 * The sample fixture project (src/test/resources/sample) has exactly:
 *   nodes: Base, Repo, Product, ProductRepo, Cart          (com.shop.*)
 *   Product    -> Base       EXTENDS     w=1
 *   ProductRepo-> Repo       IMPLEMENTS  w=1
 *   Cart       -> Product    FIELD       w=1   (List<Product> type argument)
 *   Cart       -> ProductRepo CALL       w=2   (repo.find called twice)
 *   ProductRepo-> Product    CALL        w=1   (constructor: new Product())
 * JDK types (List, ArrayList, String) must NOT appear.
 */
class ExtractorTest {

    static Graph graph;

    @BeforeAll
    static void extractSample() {
        Path sample = Path.of("src/test/resources/sample");
        graph = new Extractor().extract(sample);
    }

    @Test
    void findsAllProjectClassesAndNothingElse() {
        assertEquals(Set.of(
                "com.shop.Base", "com.shop.Repo", "com.shop.Product",
                "com.shop.ProductRepo", "com.shop.Cart"), graph.nodes());
    }

    @Test
    void extendsEdge() {
        assertEquals(1, graph.weight("com.shop.Product", "com.shop.Base", "EXTENDS"));
    }

    @Test
    void implementsEdge() {
        assertEquals(1, graph.weight("com.shop.ProductRepo", "com.shop.Repo", "IMPLEMENTS"));
    }

    @Test
    void fieldEdgeSeesGenericTypeArguments() {
        assertEquals(1, graph.weight("com.shop.Cart", "com.shop.Product", "FIELD"));
    }

    @Test
    void callEdgesAreWeightedByCallCount() {
        assertEquals(2, graph.weight("com.shop.Cart", "com.shop.ProductRepo", "CALL"));
    }

    @Test
    void constructorCallsCountAsCalls() {
        assertEquals(1, graph.weight("com.shop.ProductRepo", "com.shop.Product", "CALL"));
    }

    @Test
    void noJdkOrSelfEdges() {
        for (Graph.Edge e : graph.edges()) {
            assertTrue(graph.nodes().contains(e.src()), e.src());
            assertTrue(graph.nodes().contains(e.dst()), e.dst());
            assertNotEquals(e.src(), e.dst(), "self edge: " + e);
        }
    }

    @Test
    void writesCsvFilesThatMatchTheMetricsModuleFormat() throws Exception {
        Path out = Files.createTempDirectory("extractor-test");
        graph.writeCsv(out);
        List<String> nodes = Files.readAllLines(out.resolve("nodes.csv"));
        List<String> edges = Files.readAllLines(out.resolve("edges.csv"));
        assertEquals("class", nodes.get(0));
        assertEquals(6, nodes.size()); // header + 5 classes
        assertEquals("src,dst,type,weight", edges.get(0));
        assertTrue(edges.contains("com.shop.Cart,com.shop.ProductRepo,CALL,2"));
        assertEquals(6, edges.size()); // header + 5 edges
    }

    @Test
    void writesCallsCsvWithCalleeSignatures() throws Exception {
        Path out = Files.createTempDirectory("extractor-test");
        graph.writeCsv(out);
        List<String> calls = Files.readAllLines(out.resolve("calls.csv"));
        assertEquals("caller,callee,method,params,returns", calls.get(0));
        // Cart calls ProductRepo.find(int) -> Product, twice (2 rows)
        long findCalls = calls.stream().filter(l -> l.equals(
                "com.shop.Cart,com.shop.ProductRepo,find,int,com.shop.Product")).count();
        assertEquals(2, findCalls);
        // constructor call recorded with method <init> and void-style return
        assertTrue(calls.contains(
                "com.shop.ProductRepo,com.shop.Product,<init>,,com.shop.Product"));
    }
}
