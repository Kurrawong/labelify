from labelify import find_missing_labels, get_labels_from_repository
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


def test_get_labels_from_repository():
    iris = Path("tests/get_iris/iris.txt").read_text().splitlines()
    lbls_graph = get_labels_from_repository(Path("tests/one/background/"), iris)

    g2 = Graph().parse(
        data="""
            PREFIX dcat: <http://www.w3.org/ns/dcat#>
            PREFIX prov: <http://www.w3.org/ns/prov#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            
            <http://purl.org/linked-data/registry#status>
                rdfs:label "status" ;
            .
            
            dcat:CatalogRecord
                rdfs:label "Catalog Record"@en ;
            .
            
            prov:ActivityInfluence
                rdfs:label "Activity Influence" ;
            .
            """,
        format="turtle",
    )
    assert g2.isomorphic(lbls_graph)
