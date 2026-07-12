package com.fyp.extractor;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;

/** Class-level structural graph: nodes are FQNs, edges are typed and weighted. */
public class Graph {

    public record Edge(String src, String dst, String type) {}

    public record Call(String caller, String callee, String method,
                       String params, String returns) {}

    private final Set<String> nodes = new TreeSet<>();
    private final Map<Edge, Integer> weights = new LinkedHashMap<>();
    private final List<Call> calls = new ArrayList<>();

    /** Records a resolved call with the callee signature; same endpoint
     *  filtering as addEdge. */
    public void addCall(Call call) {
        if (call.caller().equals(call.callee())
                || !nodes.contains(call.caller()) || !nodes.contains(call.callee())) {
            return;
        }
        calls.add(call);
    }

    public List<Call> calls() {
        return calls;
    }

    public void addNode(String fqn) {
        nodes.add(fqn);
    }

    /** Adds weight to an edge; ignores self-edges and endpoints not in the node set. */
    public void addEdge(String src, String dst, String type, int weight) {
        if (src.equals(dst) || !nodes.contains(src) || !nodes.contains(dst)) {
            return;
        }
        weights.merge(new Edge(src, dst, type), weight, Integer::sum);
    }

    public Set<String> nodes() {
        return nodes;
    }

    public Set<Edge> edges() {
        return weights.keySet();
    }

    /** Weight of an edge, or 0 if absent. */
    public int weight(String src, String dst, String type) {
        return weights.getOrDefault(new Edge(src, dst, type), 0);
    }

    /** Writes nodes.csv (header "class") and edges.csv (header src,dst,type,weight). */
    public void writeCsv(Path outDir) throws IOException {
        Files.createDirectories(outDir);
        List<String> nodeLines = new ArrayList<>();
        nodeLines.add("class");
        nodeLines.addAll(nodes);
        Files.write(outDir.resolve("nodes.csv"), nodeLines);

        List<String> edgeLines = new ArrayList<>();
        edgeLines.add("src,dst,type,weight");
        weights.forEach((e, w) ->
                edgeLines.add(e.src() + "," + e.dst() + "," + e.type() + "," + w));
        Files.write(outDir.resolve("edges.csv"), edgeLines);

        List<String> callLines = new ArrayList<>();
        callLines.add("caller,callee,method,params,returns");
        calls.forEach(c -> callLines.add(String.join(",",
                c.caller(), c.callee(), c.method(), c.params(), c.returns())));
        Files.write(outDir.resolve("calls.csv"), callLines);
    }
}
