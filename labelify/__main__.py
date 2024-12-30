import argparse
import sys
from argparse import ArgumentTypeError
from getpass import getpass
from pathlib import Path
from typing import Literal as TLiteral
from typing import Optional, Union
from urllib.error import URLError
from urllib.parse import ParseResult, urlparse, urlunparse

from rdflib import Graph, URIRef
from rdflib.namespace import DCTERMS, RDF, RDFS, SDO, SKOS
from SPARQLWrapper import JSONLD, SPARQLWrapper, TURTLE
from SPARQLWrapper.SPARQLExceptions import EndPointNotFound, Unauthorized

from labelify.utils import get_namespace, list_of_predicates_to_alternates

__version__ = [v for v in open(Path(__file__).parent.parent.resolve() / "pyproject.toml").readlines() if v.startswith("version")][0].split('"')[1]


def get_labelling_predicates(l_arg):
    labels = []
    if Path(l_arg).is_file():
        labels.extend([URIRef(label.strip()) for label in open(l_arg).readlines()])
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
) -> set[URIRef]:
    """Gets all the nodes missing labels

    :param graph: the graph to look for nodes in
    :param context_graph: the additional context to search in for labels
    :param labelling_predicates: the IRIs of the label predicates to look for. Default is dcterms:title, rdfs:label, schema:name, skos:prefLabel
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
            "You have indicated context nodes should be included in label search by setting evaluate_context_nodes"
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
        # ignore rdf:type as it's problematic to document for its prefix is never bound
        if n != RDF.type:
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


def extract_labels(
        iris: [],
        p: Union[Path, ParseResult],
        timeout: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None
) -> Graph:

    q = """
        PREFIX dcterms: <http://purl.org/dc/terms/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX schema: <https://schema.org/>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

        CONSTRUCT {
            ?iri 
                rdfs:label ?label ;
                schema:description ?desc ;
                rdfs:seeAlso ?seeAlso ;
            .
        }
        WHERE {
            VALUES ?t {
                skos:prefLabel
                dcterms:title                        
                rdfs:label
                schema:name
            }
            
            VALUES ?iri {
                XXXX
            }
            
            ?iri ?t ?label .
            OPTIONAL {
                VALUES ?dt {
                    skos:definition
                    dcterms:description                        
                    rdfs:comment
                    schema:description
                }
                 
                ?iri ?dt ?desc 
            }
            OPTIONAL { ?iri rdfs:seeAlso ?seeAlso }                
        }
        """.replace("XXXX", "".join(["<" + x.strip() + ">\n                " for x in iris]).strip())

    if isinstance(p, ParseResult):
        sparql = SPARQLWrapper(p.geturl())
        sparql.setReturnFormat(TURTLE)
        sparql.setTimeout(timeout)
        if username and not password:
            sparql.setCredentials(user=username, passwd=getpass("password:"))
        elif username and password:
            sparql.setCredentials(user=username, passwd=password)
        sparql.setQuery(q)
        try:
            g = Graph().parse(data=sparql.queryAndConvert())
        except (URLError, Unauthorized, EndPointNotFound, TimeoutError) as e:
            print(e)
            exit(1)
    elif p.is_file():
        g = Graph().parse(p)
    elif p.is_dir():
        g = Graph()
        for f in p.glob("**/*"):
            g.parse(f)

    return_g = Graph()
    for r in g.query(q):
        return_g.add(r)

    return return_g


def get_triples_from_sparql_endpoint(args: argparse.Namespace) -> Graph:
    g = Graph()
    offset = 0
    batch_size = 50000
    n_results = batch_size
    url = urlunparse(args.input)
    if not args.raw:
        print(
            f"Loading triples from {url}, using graph: {'default' if not args.graph else args.graph}"
        )
        print(f"\tbatch_size: {batch_size}")
    sparql = SPARQLWrapper(endpoint=url, defaultGraph=args.graph)
    sparql.setReturnFormat(JSONLD)
    sparql.setTimeout(args.timeout)
    if args.username and not args.password:
        sparql.setCredentials(user=args.username, passwd=getpass("password:"))
        if not args.raw:
            print("\n")
    elif args.username and args.password:
        sparql.setCredentials(user=args.username, passwd=args.password)
    while n_results == batch_size:
        sparql.setQuery(
            """
        construct {{
            ?s ?p ?o .
        }}
        where {{
            ?s ?p ?o .
        }}
        order by ?s
        limit {}
        offset {}
        """.format(
                batch_size, offset
            )
        )
        try:
            g_part = sparql.queryAndConvert()
            n_results = len(g_part)
            offset += batch_size
        except (URLError, Unauthorized, EndPointNotFound, TimeoutError) as e:
            print(e)
            exit(1)
        g += g_part
        if not args.raw:
            print(
                f"\tfetched: {len(g):,}",
                end="\r" if n_results == batch_size else "\n\n",
                flush=True,
            )
    return g


def setup_cli_parser(args=None):
    def url_file_or_folder(input: str) -> ParseResult | Path:
        parsed = urlparse(input)
        if all([parsed.scheme, parsed.netloc]):
            return parsed
        path = Path(input)
        if path.is_file():
            return path
        if path.is_dir():
            return path
        raise argparse.ArgumentTypeError(
            f"{input} is not a valid input. Must be a file, folder or sparql endpoint"
        )

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version="{version}".format(version=__version__),
    )

    parser.add_argument(
        "-x",
        "--extract",
        help="Extract labels for IRIs in a given file ending .txt from a given folder of RDF files or a SPARQL endpoint",
        type=url_file_or_folder,
    )

    parser.add_argument(
        "input",
        help="File, Folder or Sparql Endpoint to read RDF from",
        type=url_file_or_folder,
    )

    parser.add_argument(
        "-c",
        "--context",
        help="labels for the input, can be a File, Folder, or SPARQL endpoint.",
        type=url_file_or_folder,
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
             "the path of a file containing labelling IRIs, one per line may be supplied. Default is skos:prefLabel, dcterms:title, rdfs:label, schema:name=",
        default=",".join([str(x) for x in [SKOS.prefLabel, DCTERMS.title, RDFS.label, SDO.name]]),
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
        "-u",
        "--username",
        type=str,
        default=None,
        dest="username",
        help="sparql username",
        required=False,
    )

    parser.add_argument(
        "-p",
        "--password",
        type=str,
        default=None,
        dest="password",
        help="sparql password",
        required=False,
    )

    parser.add_argument(
        "-g",
        "--graph",
        type=str,
        default=None,
        dest="graph",
        help="named graph to query (only used if input is a sparql endpoint)",
        required=False,
    )

    parser.add_argument(
        "-r",
        "--raw",
        dest="raw",
        action="store_true",
        help="Only output the nodes with missing labels. one per line",
    )

    parser.add_argument(
        "-t",
        "--timeout",
        type=int,
        default=15,
        dest="timeout",
        help="timeout in seconds",
        required=False,
    )

    parser.add_argument(
        "--getlabels",
        help="Gets labels for a given list of IRIs from RDF files in a given location",
        type=str,
    )

    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Output file for IRI information (normal mode) or labels in RDF (when using -x/--extract)",
        required=False,
    )

    return parser.parse_args(args)


def output_labels(iris_file, source: Path, dest: Path = None):
    if iris_file.suffix != ".txt":
        raise argparse.ArgumentTypeError(
            "When specifying --extract, you must profile a .txt file containing IRIs without labels, one per line")

    iris = iris_file.read_text().splitlines()
    res = extract_labels(iris, source)
    res.bind("rdf", RDF)
    if dest:
        o = Path(dest)
        if o.is_file():
            # the RDF file exists, so add to it
            (res + Graph().parse(o)).serialize(format="longturtle", destination=o)
        else:
            res.serialize(format="longturtle", destination=o)
    else:
        print(res.serialize(format="longturtle"))


def cli(args=None):
    if args is None:  # vocexcel run via entrypoint
        args = sys.argv[1:]

    args = setup_cli_parser(args)

    # -v version auto-handled here

    if args.extract:
        output_labels(args.extract, args.input, args.output)
        exit()

    if isinstance(args.input, ParseResult):
        g = get_triples_from_sparql_endpoint(args)
    elif args.input.is_dir():
        g = Graph()
        for file in args.input.glob("**/*.ttl"):
            g.parse(file)
    else:
        g = Graph().parse(args.input)

    cg = None

    if args.supress == "true":
        exit()

    if args.context is not None:
        cg = Graph()
        if not args.raw:
            print("Loading given context")
        if args.context.is_file():
            if not args.raw:
                print(f"Loading {args.context}")
            cg.parse(args.context)
        if args.context.is_dir():
            for f in args.context.glob("*.ttl"):
                if not args.raw:
                    print(f"Loading {f}")
                cg.parse(f)
        if not args.raw:
            print("\n")
    else:
        if not args.raw:
            print("No additional context supplied\n")

    labelling_predicates = get_labelling_predicates(args.labels)
    if not args.raw:
        print(f"Using labelling predicates:")
        for label in labelling_predicates:
            print("\t" + label)
        print("\n")
        print("".center(80, "="), end="\n\n")

    nml = find_missing_labels(
        g,
        cg,
        labelling_predicates,
        args.nodetype,
        True if args.evaluate == "true" else False,
    )

    if args.output:
        if not args.raw:
            raise ArgumentTypeError("If -o/-output is specified, -r/raw must also be specified")
        else:
            o = Path(args.output)
            if o.suffix != ".txt":
                raise ArgumentTypeError("If specifying -o/--output, you must indicate a file with the file ending .txt")
            else:
                if o.is_file():
                    # the file already exists, so add to it, deduplicatively
                    iris = o.read_text().splitlines()
                    # drop blank lines
                    iris = set(list(filter(None, iris)))

                    # add label-less IRIs to list received from file
                    for uri in nml:
                        iris.add(str(uri))

                    # we-issue the file with existing IRIs, new label-less IRIs, deduplicated
                    with open(o, "w") as o_f:
                        for uri in sorted(set(iris)):
                            o_f.write(uri + "\n")
                else:
                    # the file doesn't exist, so create it and add to it
                    with open(o, "w") as o_f:
                        for uri in sorted(nml):
                            o_f.write(uri + "\n")
    else:
        if args.raw:
            for uri in sorted(nml):
                print(uri)
        else:
            namespace: dict = {}
            for uri in nml:
                ns = get_namespace(uri)
                if not namespace.get(ns):
                    namespace[ns] = [uri]
                else:
                    namespace[ns].append(uri)
            print(f"Missing {len(nml)} labels from {len(namespace.keys())} namespaces")
            for i, ns in enumerate(sorted(namespace.keys()), 1):
                print(f"\n{i}. " + ns)
                for uri in sorted(namespace[ns]):
                    print("\t" + uri.replace(ns, ""))


if __name__ == "__main__":
    retval = cli(sys.argv[1:])
    if retval is not None:
        sys.exit(retval)
