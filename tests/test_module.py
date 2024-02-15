from labelify import get_missing_labels
from rdflib import Graph, URIRef
from rdflib.namespace import RDFS, SKOS
import glob


def test_with_cg():
    g = Graph().parse("tests/one/data-access-rights.ttl")
    cg = Graph()
    for c in glob.glob("tests/one/background/*.ttl"):
        cg.parse(c)

    missing = get_missing_labels(g, cg, [SKOS.prefLabel, RDFS.label], "objects")

    print(missing)

    assert len(missing) == 1

    assert next(iter(missing)) == URIRef("https://linked.data.gov.au/org/gsq")


def test_without_cg():
    g = Graph().parse("tests/one/data-access-rights.ttl")

    missing = get_missing_labels(g, None, [SKOS.prefLabel, RDFS.label], "objects")
    assert len(missing) == 7
