import argparse
import importlib.metadata
import sys
from argparse import ArgumentTypeError
from getpass import getpass
from pathlib import Path
from typing import List, Optional
from typing import Literal as TLiteral
from urllib.error import URLError
from urllib.parse import ParseResult, urlparse, urlunparse

from kurra.utils import guess_format_from_data, load_graph
from kurra.fuseki import query
from rdflib import Graph, URIRef
from rdflib.namespace import DCTERMS, RDF, RDFS, SDO, SKOS
from SPARQLWrapper import JSONLD, TURTLE, SPARQLWrapper
from SPARQLWrapper.SPARQLExceptions import EndPointNotFound, Unauthorized

from labelify.utils import get_namespace, list_of_predicates_to_alternates

__version__ = importlib.metadata.version(__package__)


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
    target: Graph | str | Path,
    context: Path | ParseResult | Graph | str = None,
    labelling_predicates: [URIRef] = [
        DCTERMS.title,
        RDFS.label,
        SDO.name,
        SKOS.prefLabel,
    ],
    evaluate_context_nodes: bool = False,
) -> set[URIRef]:
    """Gets all the nodes missing labels

    :param target: the graph to look for nodes in
    :param context: the additional context to search in for labels: an RDF file, folder containing RDF files or a SPARQL Endpoint
    :param labelling_predicates: the IRIs of the label predicates to look for. Default is dcterms:title, rdfs:label, schema:name, skos:prefLabel
    :param evaluate_context_nodes: whether (True) or not (False) to include Ss, Ps, & Os or all of the nodes in the
    context_graph when looking for nodes missing labels
    :return:
    """
    if evaluate_context_nodes and context is None:
        raise ValueError(
            "You have indicated context nodes should be included in label search by setting evaluate_context_nodes"
            "to True but context_graph is None"
        )

    target = load_graph(target)

    if evaluate_context_nodes:
        target += context

    s = set(target.subjects())
    p = set(target.predicates())
    o = set(target.objects())
    nodes = set(s).union(p).union(o)
    nodes_missing = set()
    for n in nodes:
        # ignore rdf:type as it's problematic to document for its prefix is never bound
        if n != RDF.type:
            # ignore Blank Nodes
            if not isinstance(n, URIRef):
                continue

            # ignore nodes that have a value for any of the labelling predicates
            if target.value(n, list_of_predicates_to_alternates(labelling_predicates)):
                continue

            nodes_missing.add(n)

    # ignore any node that is labelled in the context
    if context is not None:
        if isinstance(context, ParseResult) or (isinstance(context, str) and context.startswith("http")):
            if isinstance(context, ParseResult):
                sparql_endpoint = context.geturl()
            else:
                sparql_endpoint = context

            # make missing list into a query insert
            q = """
                PREFIX dcterms: <http://purl.org/dc/terms/>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                PREFIX schema: <https://schema.org/>
                PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
                
                SELECT DISTINCT ?iri
                WHERE {
                    VALUES ?iri {
                        XXXX
                    }
                    VALUES ?t {
                        skos:prefLabel
                        dcterms:title                        
                        rdfs:label
                        schema:name
                    }
                    
                    ?iri ?t ?label .
                }
                """.replace(
                "XXXX", "".join(["<" + x.strip() + ">\n                        " for x in nodes_missing]).strip()
            )
            r = query(sparql_endpoint, q, return_python=True, return_bindings_only=True)
            for row in r:
                nodes_missing.remove(URIRef(row["iri"]["value"]))
        elif isinstance(context, Graph) or isinstance(context, Path) or isinstance(context, str):
            if isinstance(context, Graph):
                pass
            elif isinstance(context, Path) or isinstance(context, str):
                context = load_graph(context)

            still_missing = nodes_missing.copy()
            for n in nodes_missing:
                if context.value(
                    n, list_of_predicates_to_alternates(labelling_predicates)
                ):
                    still_missing.remove(n)
            nodes_missing = still_missing

    return nodes_missing


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


def extract_labels(
    iris: [],
    labels_source: Path | ParseResult | Graph | str,
    timeout: Optional[int] = 20,
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> Graph:
    def query_sparql_endpoint(sparql_endpoint: str | ParseResult, query: str):
        if isinstance(sparql_endpoint, str):
            sparql_endpoint = urlparse(sparql_endpoint)

        sparql = SPARQLWrapper(sparql_endpoint.geturl())
        sparql.setReturnFormat(TURTLE)
        sparql.setTimeout(timeout)
        if username and not password:
            sparql.setCredentials(user=username, passwd=getpass("password:"))
        elif username and password:
            sparql.setCredentials(user=username, passwd=password)
        sparql.setQuery(query)
        try:
            return Graph().parse(data=sparql.queryAndConvert())
        except (URLError, Unauthorized, EndPointNotFound, TimeoutError) as e:
            print(e)
            exit(1)

    # make the query
    q = """
            PREFIX dcterms: <http://purl.org/dc/terms/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX schema: <https://schema.org/>
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

            CONSTRUCT {
                ?iri 
                    schema:name ?label ;
                    schema:description ?desc ;
                    schema:url ?seeAlso ;
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

                FILTER (lang(?label) = "en" || lang(?label) = "")

                OPTIONAL {
                    VALUES ?dt {
                        skos:definition
                        dcterms:description                        
                        rdfs:comment
                        schema:description
                    }

                    ?iri ?dt ?desc .

                    FILTER (lang(?desc) = "en" || lang(?desc) = "")
                }
                OPTIONAL { ?iri rdfs:seeAlso ?seeAlso }                
            }
            """.replace(
        "XXXX", "".join(["<" + x.strip() + ">\n                " for x in iris]).strip()
    )

    # make the graph from the given source
    if (
        isinstance(labels_source, str) and labels_source.startswith("http")
    ) or isinstance(labels_source, ParseResult):
        return query_sparql_endpoint(labels_source, q)

    if isinstance(labels_source, Graph):
        g = labels_source
    elif isinstance(labels_source, str):
        g = Graph().parse(labels_source, guess_format_from_data(labels_source))
    elif isinstance(labels_source, Path):
        if labels_source.is_file():
            g = Graph().parse(labels_source)
        elif labels_source.is_dir():
            g = Graph()
            for f in labels_source.glob("**/*"):
                g.parse(f)

    # query the graph
    return_g = Graph()
    for r in g.query(q):
        return_g.add(r)

    return return_g

    return return_g


def output_labels(iris: Path | List, labels_source: Path, dest: Path = None):
    if isinstance(iris, Path):
        if iris.suffix != ".txt":
            raise argparse.ArgumentTypeError(
                "When specifying --extract, you must profile a .txt file containing IRIs without labels, one per line"
            )

        iris = iris.read_text().splitlines()

    res = extract_labels(iris, labels_source)
    res.bind("rdf", RDF)
    if dest is not None:
        o = Path(dest)
        if o.is_file():
            # the RDF file exists, so add to it
            (res + Graph().parse(o)).serialize(format="longturtle", destination=o)
        else:
            res.serialize(format="longturtle", destination=o)
    else:
        print(res.serialize(format="longturtle"))


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
        default=",".join(
            [str(x) for x in [SKOS.prefLabel, DCTERMS.title, RDFS.label, SDO.name]]
        ),
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

    # if args.context is not None:
    #     cg = Graph()
    #     if not args.raw:
    #         print("Loading given context")
    #     if args.context.is_file():
    #         if not args.raw:
    #             print(f"Loading {args.context}")
    #         cg.parse(args.context)
    #     if args.context.is_dir():
    #         for f in args.context.glob("*.ttl"):
    #             if not args.raw:
    #                 print(f"Loading {f}")
    #             cg.parse(f)
    #     if not args.raw:
    #         print("\n")
    # else:
    #     if not args.raw:
    #         print("No additional context supplied\n")

    labelling_predicates = get_labelling_predicates(args.labels)
    if not args.raw:
        print(f"Using labelling predicates:")
        for label in labelling_predicates:
            print("\t" + label)
        print("\n")
        print("".center(80, "="), end="\n\n")

    nml = find_missing_labels(
        g,
        args.context,
        labelling_predicates,
        True if args.evaluate == "true" else False,
    )

    if args.output:
        if not args.raw:
            raise ArgumentTypeError(
                "If -o/-output is specified, -r/raw must also be specified"
            )
        else:
            o = Path(args.output)
            if o.suffix != ".txt":
                raise ArgumentTypeError(
                    "If specifying -o/--output, you must indicate a file with the file ending .txt"
                )
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
