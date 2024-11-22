from labelify import find_missing_labels, extract_labels
from rdflib import Graph, URIRef
from rdflib.namespace import RDFS, SKOS
import glob
from pathlib import Path


def test_with_cg():
    g = Graph().parse("tests/one/data-access-rights.ttl")
    cg = Graph()
    for c in glob.glob("tests/one/background/*.ttl"):
        cg.parse(c)

    missing = find_missing_labels(g, cg, [SKOS.prefLabel, RDFS.label], "objects")

    assert len(missing) == 1

    assert next(iter(missing)) == URIRef("https://linked.data.gov.au/org/gsq")


def test_without_cg():
    g = Graph().parse("tests/one/data-access-rights.ttl")

    missing = find_missing_labels(g, None, [SKOS.prefLabel, RDFS.label], "objects")
    assert len(missing) == 7


def test_extract_labels():
    # generate an IRI list from an RDF file
    vocab_file = Path(Path(__file__).parent / "one/data-access-rights.ttl")
    vocab_graph = Graph().parse(vocab_file)
    iris = find_missing_labels(vocab_graph)

    assert len(iris) == 23

    context_dir = Path(Path(__file__).parent / "one/background")
    labels_rdf = extract_labels(iris, context_dir)

    assert len(labels_rdf) == 27
