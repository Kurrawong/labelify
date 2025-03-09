from pathlib import Path

from rdflib import Graph

from labelify import extract_labels, find_missing_labels


def test_iri_list():
    g = Graph().parse("tests/one/data-access-rights.ttl")
    missing = find_missing_labels(g)
    assert len(missing) == 22


def test_make_labels():
    g = Graph().parse("tests/one/data-access-rights.ttl")
    missing = find_missing_labels(g)
    labels = extract_labels(missing, Path(__file__).parent / "one" / "background")
    assert len(labels) == 26


def test_labels_to_file():
    iris = Path(Path(__file__).parent / "one" / "iris.txt").read_text().splitlines()
    labels = extract_labels(iris, Path(__file__).parent / "one" / "background")
    g2 = Graph().parse(Path(__file__).parent / "one" / "labels.ttl")

    assert labels.isomorphic(g2)
