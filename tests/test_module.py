from labelify import find_missing_labels, extract_labels
from rdflib import Graph, URIRef
from rdflib.namespace import RDFS, SKOS
import glob
from pathlib import Path
import urllib.request


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
    iris = find_missing_labels(vocab_file)

    assert len(iris) == 22

    labels_source = Path(Path(__file__).parent / "one/background")
    labels_rdf = extract_labels(iris, labels_source)

    assert len(labels_rdf) == 26


def test_extract_with_context_sparql_endpoint():
    # SPARQL endpoint must be online
    # delivering Semantic Background
    with urllib.request.urlopen("http://localhost:3030") as response:
        assert response.getcode() == 200

    iris = [
        "https://example.com/demo-vocabs-catalogue" ,
        "http://purl.org/dc/terms/hasPart" ,
        "https://schema.org/image" ,
        "http://purl.org/linked-data/registry#status" ,
        "https://olis.dev/isAliasFor" ,
        "http://www.w3.org/2004/02/skos/core#notation" ,
        "https://schema.org/name" ,
        "http://www.w3.org/2004/02/skos/core#hasTopConcept" ,
        "https://schema.org/description" ,
        "http://www.w3.org/2004/02/skos/core#definition" ,
        "http://www.w3.org/2004/02/skos/core#ConceptScheme" ,
        "https://schema.org/creator" ,
        "https://schema.org/dateModified" ,
        "https://olis.dev/VirtualGraph" ,
        "https://schema.org/mathExpression" ,
        "http://www.w3.org/2004/02/skos/core#historyNote" ,
        "http://www.w3.org/2004/02/skos/core#inScheme" ,
        "https://schema.org/codeRepository" ,
        "https://schema.org/publisher" ,
        "http://www.w3.org/2004/02/skos/core#prefLabel" ,
        "https://kurrawong.ai" ,
        "http://www.w3.org/2000/01/rdf-schema#label" ,
        "https://linked.data.gov.au/def/reg-statuses/experimental" ,
        "https://schema.org/dateCreated" ,
        "http://www.w3.org/2004/02/skos/core#Concept" ,
        "http://www.w3.org/ns/dcat#Catalog" ,
        "http://www.w3.org/2004/02/skos/core#altLabel" ,
    ]

    assert len(extract_labels(iris, "http://localhost:3030/ds/query")) == 54