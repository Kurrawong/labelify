import argparse
import os
from pathlib import Path

from rdflib import Graph
from rdflib.namespace import DCTERMS, RDFS, SDO, SKOS


def get_args():
    def file_path(path):
        if os.path.isfile(path):
            return path
        else:
            raise argparse.ArgumentTypeError(f"{path} is not a valid file")

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "input", help="Input RDF file to extract labels from", type=file_path
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = get_args()
    input_file_path = Path(args.input)
    g = Graph().parse(input_file_path)

    g2 = Graph()
    for s, o in g.subject_objects(
        RDFS.label | SKOS.prefLabel | SDO.name | DCTERMS.title
    ):
        g2.add((s, RDFS.label, o))

    parts = os.path.splitext(str(input_file_path))
    new_file_path = Path(parts[0] + "-labels" + parts[1])
    g2.serialize(destination=new_file_path, format="longturtle")
