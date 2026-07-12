package com.fyp.extractor;

import com.github.javaparser.JavaParser;
import com.github.javaparser.ParserConfiguration;
import com.github.javaparser.ast.CompilationUnit;
import com.github.javaparser.ast.body.FieldDeclaration;
import com.github.javaparser.ast.body.TypeDeclaration;
import com.github.javaparser.ast.expr.MethodCallExpr;
import com.github.javaparser.ast.expr.ObjectCreationExpr;
import com.github.javaparser.ast.type.ClassOrInterfaceType;
import com.github.javaparser.resolution.declarations.ResolvedReferenceTypeDeclaration;
import com.github.javaparser.symbolsolver.JavaSymbolSolver;
import com.github.javaparser.symbolsolver.resolution.typesolvers.CombinedTypeSolver;
import com.github.javaparser.symbolsolver.resolution.typesolvers.JavaParserTypeSolver;
import com.github.javaparser.symbolsolver.resolution.typesolvers.ReflectionTypeSolver;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.stream.Stream;

/**
 * Extracts a class-level structural graph from a Java source tree.
 * Edge types: CALL (method + constructor calls, weighted by count),
 * EXTENDS, IMPLEMENTS, FIELD (declared field types incl. generic type args).
 * Only edges whose both endpoints are project classes are kept.
 */
public class Extractor {

    private int unresolvedCalls = 0;
    private int totalCalls = 0;

    public Graph extract(Path repo) {
        List<Path> sourceRoots = findSourceRoots(repo);

        CombinedTypeSolver solver = new CombinedTypeSolver(new ReflectionTypeSolver());
        for (Path root : sourceRoots) {
            solver.add(new JavaParserTypeSolver(root));
        }
        ParserConfiguration config = new ParserConfiguration()
                .setSymbolResolver(new JavaSymbolSolver(solver))
                .setLanguageLevel(ParserConfiguration.LanguageLevel.BLEEDING_EDGE);
        JavaParser parser = new JavaParser(config);

        List<CompilationUnit> units = new ArrayList<>();
        for (Path root : sourceRoots) {
            try (Stream<Path> files = Files.walk(root)) {
                for (Path p : files.filter(f -> f.toString().endsWith(".java")).toList()) {
                    try {
                        parser.parse(p).getResult().ifPresent(units::add);
                    } catch (IOException e) {
                        System.err.println("WARN: cannot parse " + p + ": " + e.getMessage());
                    }
                }
            } catch (IOException e) {
                throw new RuntimeException(e);
            }
        }

        Graph graph = new Graph();
        // pass 1: nodes
        for (CompilationUnit cu : units) {
            cu.findAll(TypeDeclaration.class).forEach(td ->
                    td.getFullyQualifiedName().ifPresent(fqn -> graph.addNode((String) fqn)));
        }
        // pass 2: edges
        for (CompilationUnit cu : units) {
            for (TypeDeclaration<?> td : cu.findAll(TypeDeclaration.class)) {
                Optional<String> fqnOpt = td.getFullyQualifiedName().map(Object::toString);
                if (fqnOpt.isEmpty()) continue;
                String self = fqnOpt.get();

                td.toClassOrInterfaceDeclaration().ifPresent(cid -> {
                    cid.getExtendedTypes().forEach(t ->
                            resolve(t).ifPresent(fqn -> graph.addEdge(self, fqn, "EXTENDS", 1)));
                    cid.getImplementedTypes().forEach(t ->
                            resolve(t).ifPresent(fqn -> graph.addEdge(self, fqn, "IMPLEMENTS", 1)));
                });

                // element type plus generic type arguments (List<Product> -> Product)
                for (FieldDeclaration fd : td.getFields()) {
                    fd.getElementType().findAll(ClassOrInterfaceType.class).forEach(t ->
                            resolve(t).ifPresent(fqn -> graph.addEdge(self, fqn, "FIELD", 1)));
                }

                td.findAll(MethodCallExpr.class).forEach(call -> {
                    totalCalls++;
                    try {
                        ResolvedReferenceTypeDeclaration decl =
                                call.resolve().declaringType();
                        graph.addEdge(self, decl.getQualifiedName(), "CALL", 1);
                    } catch (RuntimeException e) {
                        unresolvedCalls++;
                    }
                });
                td.findAll(ObjectCreationExpr.class).forEach(call -> {
                    totalCalls++;
                    try {
                        graph.addEdge(self,
                                call.resolve().declaringType().getQualifiedName(), "CALL", 1);
                    } catch (RuntimeException e) {
                        unresolvedCalls++;
                    }
                });
            }
        }
        return graph;
    }

    private Optional<String> resolve(ClassOrInterfaceType type) {
        try {
            return Optional.of(type.resolve().asReferenceType().getQualifiedName());
        } catch (RuntimeException e) {
            return Optional.empty();
        }
    }

    public int unresolvedCalls() {
        return unresolvedCalls;
    }

    public int totalCalls() {
        return totalCalls;
    }

    /** Source roots: every directory matching *&#47;src/main/java; the repo root if none. */
    static List<Path> findSourceRoots(Path repo) {
        try (Stream<Path> dirs = Files.walk(repo)) {
            List<Path> roots = dirs
                    .filter(Files::isDirectory)
                    .filter(p -> p.endsWith(Path.of("src", "main", "java")))
                    .toList();
            return roots.isEmpty() ? List.of(repo) : roots;
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
    }
}
