from urllib.parse import urlparse

from rdflib import URIRef


def list_of_predicates_to_alternates(list_of_predicates):
    return eval(" | ".join([f"URIRef('{al}')" for al in list_of_predicates]))


def get_namespace(uri: URIRef | str) -> str:
    parsed = urlparse(uri)
    if parsed.fragment:
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}#"
    else:
        path = "/".join(parsed.path.split("/")[:-1])
        return f"{parsed.scheme}://{parsed.netloc}{path}"
