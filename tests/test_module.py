import glob
from pathlib import Path

import httpx
import kurra.db
from kurra.db import upload, sparql
from rdflib import Graph, URIRef
from rdflib.namespace import RDFS, SKOS

from labelify import extract_labels, find_missing_labels


def test_iris_without_context():
    g = Graph().parse("tests/one/data-access-rights.ttl")

    missing = find_missing_labels(g, None, [SKOS.prefLabel, RDFS.label])
    assert len(missing) == 23


def test_iris_with_context_folder():
    g = Graph().parse("tests/one/data-access-rights.ttl")
    cg = Graph()
    for c in glob.glob("tests/one/background/*.ttl"):
        cg.parse(c)

    missing = find_missing_labels(g, cg, [SKOS.prefLabel, RDFS.label], True)

    assert len(missing) == 1

    assert next(iter(missing)) == URIRef("https://linked.data.gov.au/org/gsq")


def test_iris_with_context_file():
    missing = find_missing_labels(
        Path(__file__).parent / "manifest.ttl",
    )

    assert len(missing) == 9

    missing = find_missing_labels(
        Path(__file__).parent / "manifest.ttl",
        context=Path(__file__).parent / "labels-2.ttl",
    )

    # reduces the above 9 by 2 to 7
    assert len(missing) == 7


def test_iris_with_context_sparql(fuseki_container):
    port = fuseki_container.get_exposed_port(3030)
    SPARQL_ENDPOINT = f"http://localhost:{port}/ds"
    missing = find_missing_labels(
        Path(__file__).parent / "manifest.ttl",
    )

    assert len(missing) == 9

    # add some labels to the SPARQL store, should see a reduction in IRIs missing labels
    five_labels = """
    PREFIX schema: <https://schema.org/>
    
    schema:name
        schema:name "name" ;
    .
    
    schema:description
        schema:name "description" ;
    .
    
    <https://prez.dev/ManifestResourceRoles/CatalogueData> 
        schema:name "Catalogue Data" 
    .
    
    <https://prez.dev/ManifestResourceRoles/ResourceData> 
        schema:name "Resource Data" 
    .
    
    <http://www.w3.org/ns/dx/prof/hasResource>
        schema:name "has resource" 
    .
    """

    upload(SPARQL_ENDPOINT, five_labels, graph_id="http://whatever")

    missing2 = find_missing_labels(
        Path(__file__).parent / "manifest.ttl", context=SPARQL_ENDPOINT
    )

    assert len(missing2) == 4


def test_extract_labels(fuseki_container):
    # generate an IRI list from an RDF file
    vocab_file = Path(Path(__file__).parent / "one/data-access-rights.ttl")
    iris = find_missing_labels(vocab_file)

    assert len(iris) == 22

    labels_source = Path(Path(__file__).parent / "one/background")
    labels_rdf = extract_labels(iris, labels_source)

    assert len(labels_rdf) == 26

    extra_labels = """
        PREFIX schema: <https://schema.org/>
        
        <http://purl.org/dc/terms/created> schema:name "created" .
        <http://purl.org/dc/terms/creator> schema:name "creator" .
        <http://purl.org/dc/terms/provenance> schema:name "provenance" .
        """

    SPARQL_ENDPOINT = f"http://localhost:{fuseki_container.get_exposed_port(3030)}/ds"
    kurra.db.clear_graph(SPARQL_ENDPOINT, "all", httpx.Client())
    upload(SPARQL_ENDPOINT, extra_labels, graph_id="http://example.com")
    labels_rdf = extract_labels(iris, SPARQL_ENDPOINT, httpx.Client(auth=("admin", "admin")))

    assert len(labels_rdf) == 3


def test_extract_with_context_sparql_endpoint(fuseki_container):
    SPARQL_ENDPOINT = f"http://localhost:{fuseki_container.get_exposed_port(3030)}/ds"

    iris = [
        "https://example.com/demo-vocabs-catalogue",
        "http://purl.org/dc/terms/hasPart",
        "https://schema.org/image",
        "http://purl.org/linked-data/registry#status",
        "https://olis.dev/isAliasFor",
        "http://www.w3.org/2004/02/skos/core#notation",
        "https://schema.org/name",
        "http://www.w3.org/2004/02/skos/core#hasTopConcept",
        "https://schema.org/description",
        "http://www.w3.org/2004/02/skos/core#definition",
        "http://www.w3.org/2004/02/skos/core#ConceptScheme",
        "https://schema.org/creator",
        "https://schema.org/dateModified",
        "https://olis.dev/VirtualGraph",
        "https://schema.org/mathExpression",
        "http://www.w3.org/2004/02/skos/core#historyNote",
        "http://www.w3.org/2004/02/skos/core#inScheme",
        "https://schema.org/codeRepository",
        "https://schema.org/publisher",
        "http://www.w3.org/2004/02/skos/core#prefLabel",
        "https://kurrawong.ai",
        "http://www.w3.org/2000/01/rdf-schema#label",
        "https://linked.data.gov.au/def/reg-statuses/experimental",
        "https://schema.org/dateCreated",
        "http://www.w3.org/2004/02/skos/core#Concept",
        "http://www.w3.org/ns/dcat#Catalog",
        "http://www.w3.org/2004/02/skos/core#altLabel",
    ]

    # add some labels - only 3 relevant
    some_labels = """
    PREFIX schema: <https://schema.org/>

    schema:name
        schema:name "name" ;
    .

    schema:description
        schema:name "description" ;
    .

    <https://prez.dev/ManifestResourceRoles/CatalogueData> 
        schema:name "Catalogue Data" 
    .

    <https://prez.dev/ManifestResourceRoles/ResourceData> 
        schema:name "Resource Data" 
    .

    <http://www.w3.org/ns/dx/prof/hasResource>
        schema:name "has resource" 
    .
    
    <http://purl.org/dc/terms/hasPart>
        schema:name "has part" 
    .    
    """

    upload(SPARQL_ENDPOINT, some_labels, graph_id="http://whatever")

    # will only get RDF for 3 IRIs
    rdf = extract_labels(iris, SPARQL_ENDPOINT)
    assert len(rdf) == 3


def test_find_missing_labels_sparql(fuseki_container):
    SPARQL_ENDPOINT = f"http://localhost:{fuseki_container.get_exposed_port(3030)}/ds"

    http_client = httpx.Client()

    sparql(SPARQL_ENDPOINT, "DROP ALL", http_client=http_client)

    # add all missing labels to SPARQL Endpoint
    q = """
    PREFIX schema: <https://schema.org/>
    
    INSERT DATA {    
        GRAPH <http://whatever> {
            <https://prez.dev/ManifestResourceRoles/CatalogueData> schema:name "Catalogue Data" . 
            <https://schema.org/name> schema:name "name" .
            <http://www.w3.org/ns/dx/prof/hasArtifact> schema:name "has artifact" .
            <https://prez.dev/Manifest> schema:name "Manifest" .
            <http://www.w3.org/ns/dx/prof/hasRole> schema:name "has role" .
            <https://prez.dev/ManifestResourceRoles/ResourceData> schema:name "Resource Data" .
            <http://www.w3.org/ns/dx/prof/hasResource> schema:name "has resource" .
            <https://prez.dev/ManifestResourceRoles/CatalogueAndResourceModel> schema:name "Catalogue And Resource Model" . 
            # <https://schema.org/description> schema:name "description" .  
        }
    }
    """
    sparql(SPARQL_ENDPOINT, q, http_client=http_client)

    ml = find_missing_labels(Path(__file__).parent / "manifest.ttl", SPARQL_ENDPOINT, http_client=http_client)
    print(ml)
    assert len(list(ml)) == 1