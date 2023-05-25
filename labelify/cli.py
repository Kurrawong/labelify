import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent.parent))
from labelify import __version__
import os
import argparse
from rdflib import Graph, URIRef
from rdflib.paths import Path as PredicatePath
from rdflib.paths import AlternativePath
from rdflib.namespace import RDFS, SDO, SKOS
from itertools import chain
from labelify.utils import list_of_predicates_to_alternates
from typing import Literal as TLiteral
from typing import Optional


def get_labelling_predicates(l_arg):
    labels = [RDFS.label]
    if l_arg == str(RDFS.label):
        pass
    elif Path(l_arg).is_file():
        labels.extend(open(l_arg).readlines())
    elif "," in l_arg:
        labels.extend([URIRef(item) for item in l_arg.split(",")])
    elif l_arg is not None:
        labels.extend([URIRef(l_arg)])
    else:
        raise ValueError(
            "You must supply either a comma-delimited string of IRIs or a file containing IRIs, "
            "one per line if you indicate a labelling predicates command line argument (-l)"
        )
    return labels


def call_method(o, name):
    return getattr(o, name)()


def get_nodes_missing_labels(
    labelling_predicates: list[URIRef],
    graph: Graph,
    context_graph: Optional[Graph] = None,
    node_type: TLiteral["subjects", "predicates", "objects", "all"] = "all",
    evaluate_context_nodes: bool = False,
):
    """Gets all the nodes missing labels

    :param graph: the graph to look for nodes in
    :param context_graph: the additional context to search in for labels
    :param node_type: S, P, O or all of them
    :param evaluate_context_nodes: whether (True) or not (False) to include Ss, Ps, & Os or all of the nodes in the
    context_graph when looking for nodes missing labels
    :return:
    """
    allowed_node_types = ["subjects", "predicates", "objects", "all"]
    if node_type not in allowed_node_types:
        raise ValueError(
            f"The node_type for the function get_nodes_missing_labels must be one of {', '.join(allowed_node_types)} but instead got {node_type}"
        )

    if evaluate_context_nodes and context_graph is None:
        raise ValueError(
            "You have indicated context nodes sould be included in label search by setting evaluate_context_nodes"
            "to True but context_graph is None"
        )

    if evaluate_context_nodes:
        target_graph = graph + context_graph
    else:
        target_graph = graph

    if node_type == "all":
        s = get_nodes_missing_labels(
            labelling_predicates,
            graph,
            context_graph,
            "subjects",
            evaluate_context_nodes,
        )
        p = get_nodes_missing_labels(
            labelling_predicates,
            graph,
            context_graph,
            "predicates",
            evaluate_context_nodes,
        )
        o = get_nodes_missing_labels(
            labelling_predicates,
            graph,
            context_graph,
            "objects",
            evaluate_context_nodes,
        )
        return s.union(p).union(o)

    nodes = set()
    for n in call_method(target_graph, node_type):
        if not isinstance(n, URIRef):
            continue

        if graph.value(n, list_of_predicates_to_alternates(labelling_predicates)):
            continue

        if context_graph is not None:
            if context_graph.value(
                n, list_of_predicates_to_alternates(labelling_predicates)
            ):
                continue
        nodes.add(n)
    return nodes


def get_args():
    def file_path(path):
        if os.path.isfile(path):
            return path
        else:
            raise argparse.ArgumentTypeError(f"{path} is not a valid file")

    def dir_path(path):
        if os.path.isdir(path):
            return path
        else:
            raise argparse.ArgumentTypeError(f"{path} is not a valid directory")

    def file_or_dir_path(path):
        if os.path.isfile(path) or os.path.isdir(path):
            return path
        else:
            raise argparse.ArgumentTypeError(f"{path} is not a file or a directory")

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version="{version}".format(version=__version__),
    )

    parser.add_argument("input", help="Input RDF file being analysed", type=file_path)

    parser.add_argument(
        "-c",
        "--context",
        help="A folder path containing RDF files or a single RDF file path to the ontology(ies) containing labels for the input",
        type=file_or_dir_path,
    )

    parser.add_argument(
        "-s",
        "--supress",
        help="Produces no output if set to 'true'. This is used for testing only",
        choices=["true", "false"],
        default="false",
    )

    parser.add_argument(
        "-l",
        "--labels",
        help="A list of predicates (IRIs) to looks for that indicate labels. A comma-delimited list may be supplied or "
        "the path of a file containing labelling IRIs, one per line may be supplied. Default is RDFS.label",
        default=RDFS.label,
        type=str,
    )

    parser.add_argument(
        "-n",
        "--nodetype",
        help="The type of node you want to check for labels. Select 'subject', 'predicate', 'object' or 'all'",
        choices=["subjects", "predicates", "objects", "all"],
        default="all",
    )

    parser.add_argument(
        "-e",
        "--evaluate",
        help="Evaluate nodes in the context graphs for labels",
        choices=["true", "false"],
        default="false",
    )

    return parser.parse_args()


def main():
    args = get_args()

    g = Graph().parse(args.input)
    cg = None

    if args.supress == "true":
        exit()

    if args.context is not None:
        cg = Graph()
        print("Loading given context")
        if Path(args.context).is_file():
            print(f"Loading {args.context}")
            cg.parse(args.context)
        if Path(args.context).is_dir():
            for f in Path(args.context).glob("*.ttl"):
                print(f"Loading {f}")
                cg.parse(f)
    else:
        print("No additional context supplied")

    labelling_predicates = get_labelling_predicates(args.labels)

    nml = get_nodes_missing_labels(
        labelling_predicates,
        g,
        cg,
        args.nodetype,
        True if args.evaluate == "true" else False,
    )
    print(f"{str(args.nodetype).title()} missing labels ({len(nml)}):")
    for x in nml:
        print(x)


if __name__ == "__main__":
    main()
