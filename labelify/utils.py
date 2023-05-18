import pickle
from pathlib import Path
from rdflib import Graph, URIRef


def parse_or_load(p: Path) -> Graph:
    """Parses an RDF file into a Graph unless it can read an already parsed pickled version first"""
    pkl_path = p.with_suffix(".pkl")

    if pkl_path.is_file():
        return pickle.load(open(pkl_path, "rb"))
    else:
        g = Graph().parse(p)
        pickle.dump(g, open(pkl_path, "wb"))
        return g


def list_of_predicates_to_alternates(list_of_predicates):
    return eval(" | ".join([f"URIRef('{al}')" for al in list_of_predicates]))
