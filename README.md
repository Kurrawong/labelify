# labelify 

labelify is a Python module and command line utility that identifies
unlabelled resources in a graph. It is highly configurable and works on
a number of different RDF data sources.

## Installation

labelify is on PyPI at https://pypi.org/project/labelify/ so:

    pip install labelify

or 

    poetry add labelify

will install it.

To install from it's version control repo, for the latest unstable release:

    pip install git+https://github.com/Kurrawong/labelify

## Command Line Usage

Find all missing labels in `myOntology.ttl:`

    labelify myOntology.ttl

Find missing labels for all the predicates (not subjects or objects) in
`myOntology.ttl:`

    labelify myOntology.ttl --nodetype predicates

Find all missing labels in `myOntology.ttl` taking into account the
labels which have been defined in another file called
`supportingVocab.ttl`.

*but don’t check for missing labels in `supportingVocab.ttl`*

    labelify myOntology.ttl --context supportingVocab.ttl

Same as above but use the additional labelling predicates given in
`myLabellingPredicates.txt.`

*By default only rdfs:label is used as a labelling predicate.*

    labelify myOntology.ttl --context supportingVocab.ttl --labels myLabellingPredicates.txt

Where `myLabellingPredicates.txt` is a list of labelling predicates (one
per line and unprefixed):

    http://www.w3.org/2004/02/skos/core#prefLabel
    http://schema.org/name

Find all the missing labels in the subgraph `http://example-graph` at
the sparql endpoint `http://mytriplestore/sparql` using basic HTTP auth
to connect.

labelify will prompt for the password or it can be provided with the
`--password` flag if you dont mind it being saved to the shell history.

    labelify http://mytriplestore/sparql --graph http://example-graph --username admin

### Label Extraction

Get all the IRIs with missing labels from a local RDF file and put them
into a text file with an IRI per line:

    labelify -n all my_file.ttl -r > iris-missing-labels.txt

*note use of `-r` for simple IRI printing*

Use the output file to generate an RDF file containing the labes,
extracted from either another RDF file, a directory of RDF files or a
SPARQL endpoint:

    labelify -x iris-missing-labels.txt other-rdf-file.ttl > labels.ttl
    # or
    labelify -x iris-missing-labels.txt dir-of-rdf-files/ > labels.ttl
    # or
    labelify -x iris-missing-labels.txt http://some-sparql-endpoint.com/sparql > labels.ttl

## Command line output formats

By default, labelify will print helpful progress and configuration
messages and attempt to group the missing labels by namespace, making it
easier to quickly parse the output.

The `--raw/-r` option can be appended to any of the examples above to
tell labelify to only print the uris of objects with missing labels (one
per line) and no other messages. This is useful for command line
composition if you wish to pipe the output into another process.

## More command line options

For more help and the complete list of command line options just run
`labelify --help/-h`

As per unix conventions all the flags shown above can also be used with
short codes. i.e. `-g` is the same as `--graph`.

## Usage as a module

Print missing labels for all the objects (not subjects or predicates) in
`myOntology.ttl`, taking into account any labels which have been defined
in RDF files in the `supportingVocabs` directory.

Using `skos:prefLabel` and `rdfs:label`, but not `dcterms:title` and
`schema:name` (as per default) as the labelling predicates.

    from labelify import find_missing_labels
    from rdflib import Graph
    from rdflib.namespace import RDFS, SKOS
    import glob

    graph = Graph().parse("myOntology.ttl")
    context_graph = Graph()
    for context_file in glob.glob("supportingVocabs/*.ttl"):
        context_graph.parse(context_file)
    labelling_predicates = [SKOS.prefLabel, RDFS.label]
    nodetype = "objects"

    missing_labels = find_missing_labels(
        graph,
        context_graph,
        labelling_predicates,
        nodetype
    )
    print(missing_labels)

and, to extract labels, descriptions & seeAlso details for given IRIs
from a given directory of RDF files:

    from pathlib import Path
    from labelify import extract_labels

    iris = Path("tests/get_iris/iris.txt").read_text().splitlines()
    lbls_graph = extract_labels(Path("tests/one/background/"), iris)

## Development

### Installing from source

Clone the repository and install the dependencies

*labelify uses [Poetry](https://python-poetry.org/) to manage its
dependencies.*

    git clone git@github.com:Kurrawong/labelify.git
    cd labelify
    poetry install

You can then use labelify from the command line

    poetry shell
    python labelify/ ...

### Running tests

    poetry run pytest

### Formatting the codebase

    poetry run black . && poetry run ruff check --fix labelify/

## License

[BSD-3-Clause](https://opensource.org/license/bsd-3-clause/), if anyone
is asking.

## Contact

**KurrawongAI**  
<info@kurrawong.ai>  
<https://kurrawong.ai>
