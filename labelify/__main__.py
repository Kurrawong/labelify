import argparse
import os
import sys
from pathlib import Path
from typing import Literal as TLiteral
from typing import Optional
from textwrap import indent

from rdflib import Graph, URIRef
from rdflib.namespace import DCTERMS, RDFS, SDO, SKOS

from labelify.utils import list_of_predicates_to_alternates

__version__ = "0.0.1"


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


def find_missing_labels(
    graph: Graph,
    context_graph: Optional[Graph] = None,
    labelling_predicates: list[URIRef] = [
        DCTERMS.title,
        RDFS.label,
        SDO.name,
        SKOS.prefLabel,
    ],
    node_type: TLiteral["subjects", "predicates", "objects", "all"] = "all",
    evaluate_context_nodes: bool = False,
):
    """Gets all the nodes missing labels

    :param graph: the graph to look for nodes in
    :param context_graph: the additional context to search in for labels
    :param labelling_predicates: the IRIs of the label predicates to look for. Default is rdfs:label
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
        s = find_missing_labels(
            graph,
            context_graph,
            labelling_predicates,
            "subjects",
            evaluate_context_nodes,
        )
        p = find_missing_labels(
            graph,
            context_graph,
            labelling_predicates,
            "predicates",
            evaluate_context_nodes,
        )
        o = find_missing_labels(
            graph,
            context_graph,
            labelling_predicates,
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


def get_labels_from_repository(path_to_folder_of_files: Path, iris_with_no_labels: []):
    # load all the files in the folder
    g = Graph()
    for f in path_to_folder_of_files.glob("**/*"):
        g.parse(f)

    # create label extraction query
    q = """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX schema: <https://schema.org/>
        
        CONSTRUCT {
            ?iri 
                rdfs:label ?label ;
                schema:description ?desc ;
                rdfs:seeAlso ?seeAlso ;
            .
        }
        WHERE {
            VALUES ?iri {
xxxx
            }
            ?iri rdfs:label ?label .
            OPTIONAL { ?iri schema:description ?desc }
            OPTIONAL { ?iri rdfs:seeAlso ?seeAlso }            
        }
        """
    q = q.replace("xxxx", indent("<" + ">\n<".join(iris_with_no_labels) + ">", "                "))

    # run the query against the data
    return g.query(q)


def cli(args=None):
    if args is None:  # vocexcel run via entrypoint
        args = sys.argv[1:]

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

    parser.add_argument("input", help="Input RDF file being analysed", type=file_or_dir_path)

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

    parser.add_argument(
        "-g",
        "--getlabels",
        help="Gets labels for a given list of IRIs from RDF files in a given location",
        type=str,
    )

    args = parser.parse_args(args)

    if args.getlabels:
        if Path(args.getlabels).is_file():
            iris = Path(args.getlabels).read_text().splitlines()
        else:
            iris = args.getlabels.split(",")

        if not Path(args.input).is_dir():
            raise ValueError("ERROR: You have called the function getlabels but have not supplied a directory for the input from which to get the labels")

        print(get_labels_from_repository(Path(args.input), iris).serialize(format="longturtle").decode())
        exit()

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

    nml = find_missing_labels(
        g,
        cg,
        labelling_predicates,
        args.nodetype,
        True if args.evaluate == "true" else False,
    )
    print(f"{str(args.nodetype).title()} missing labels ({len(nml)}):")
    for x in nml:
        print(x)


if __name__ == "__main__":
    retval = cli(sys.argv[1:])
    if retval is not None:
        sys.exit(retval)
