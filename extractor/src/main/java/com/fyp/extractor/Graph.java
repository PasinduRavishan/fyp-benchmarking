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
    public record MethodDecl(String className, String methodName, String returnType, List<String> parameterTypes) {}
    public record MethodCall(String srcClass, String srcMethod, String dstClass, String dstMethod) {}

    public record Call(String caller, String callee, String method,
                       String params, String returns) {}

    private final Set<String> nodes = new TreeSet<>();
    private final Map<Edge, Integer> weights = new LinkedHashMap<>();
    private final List<MethodDecl> methods = new ArrayList<>();
    private final Set<MethodCall> methodCalls = new TreeSet<>((c1, c2) -> {
        int r = c1.srcClass().compareTo(c2.srcClass());
        if (r != 0) return r;
        r = c1.srcMethod().compareTo(c2.srcMethod());
        if (r != 0) return r;
        r = c1.dstClass().compareTo(c2.dstClass());
        if (r != 0) return r;
        return c1.dstMethod().compareTo(c2.dstMethod());
    });

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

    public void addMethod(String className, String methodName, String returnType, List<String> parameterTypes) {
        methods.add(new MethodDecl(className, methodName, returnType, parameterTypes));
    }

    public void addMethodCall(String srcClass, String srcMethod, String dstClass, String dstMethod) {
        if (srcClass.equals(dstClass) || !nodes.contains(srcClass) || !nodes.contains(dstClass)) {
            return;
        }
        methodCalls.add(new MethodCall(srcClass, srcMethod, dstClass, dstMethod));
    }

    public Set<String> nodes() {
        return nodes;
    }

    public Set<Edge> edges() {
        return weights.keySet();
    }

    public List<MethodDecl> methods() {
        return methods;
    }

    public Set<MethodCall> methodCalls() {
        return methodCalls;
    }

    /** Weight of an edge, or 0 if absent. */
    public int weight(String src, String dst, String type) {
        return weights.getOrDefault(new Edge(src, dst, type), 0);
    }

    /** Writes nodes.csv, edges.csv, methods.csv, and method_calls.csv. */
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

        List<String> methodLines = new ArrayList<>();
        methodLines.add("class,method,returnType,parameters");
        for (MethodDecl m : methods) {
            String params = String.join(";", m.parameterTypes());
            methodLines.add(m.className() + "," + m.methodName() + "," + m.returnType() + "," + params);
        }
        Files.write(outDir.resolve("methods.csv"), methodLines);

        List<String> methodCallLines = new ArrayList<>();
        methodCallLines.add("srcClass,srcMethod,dstClass,dstMethod");
        for (MethodCall mc : methodCalls) {
            methodCallLines.add(mc.srcClass() + "," + mc.srcMethod() + "," + mc.dstClass() + "," + mc.dstMethod());
        }
        Files.write(outDir.resolve("method_calls.csv"), methodCallLines);
    }
}
