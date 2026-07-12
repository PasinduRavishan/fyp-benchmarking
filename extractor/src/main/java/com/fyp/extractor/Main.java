package com.fyp.extractor;

import java.nio.file.Path;

/** CLI: java -jar extractor.jar <java-repo-path> <output-dir> */
public class Main {
    public static void main(String[] args) throws Exception {
        if (args.length != 2) {
            System.err.println("Usage: extractor <java-repo-path> <output-dir>");
            System.exit(1);
        }
        Extractor extractor = new Extractor();
        Graph graph = extractor.extract(Path.of(args[0]));
        graph.writeCsv(Path.of(args[1]));
        System.out.printf("nodes=%d edges=%d calls_resolved=%d/%d%n",
                graph.nodes().size(), graph.edges().size(),
                extractor.totalCalls() - extractor.unresolvedCalls(), extractor.totalCalls());
    }
}
