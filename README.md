# labelify 

labelify is a Python module and command line utility that identifies unlabelled resources in RDF graphs and can 
extract labels for them from external resources. 

If you would like to use the labelify tool directly, we provide an online GUI for it 
[here](https://tools.dev.kurrawong.ai/). 

## Installation

### Command line use

Clone the labelify repository:

    git clone https://github.com/Kurrawong/labelify somewhere

Then, install it using Python's [Poetry package manager](https://python-poetry.org/) from within the cloned repository's
root folder:

    poetry install

If you don't install it this way, you can still use it as a Command Line Interface by running it as a Python script. 
From within the cloned repository's root directory:

    python -m labelify -h 

...for the help command.

### Pyton library

labelify is on PyPI at https://pypi.org/project/labelify/ so:

    pip install labelify

or 

    poetry add labelify

will install it.

To install from it's version control repo, for the latest unstable release:

    pip install git+https://github.com/Kurrawong/labelify

## Use

### Command Line

To run labelify from the command line, you must have labelify installed as a script or you run it via Python - see 
above. Then, labelify can tell you all about its command line options, just run:

    labelify -h

for "help".

#### Simple use

Find all missing labels in `data.ttl:`

    labelify data.ttl

Find all missing labels in `data.ttl` taking into account the
labels which have been defined in another file called `labels.ttl`.

*but don’t check for missing labels in `supportingVocab.ttl`*

    labelify data.ttl --context labels.ttl

Same as above but use the additional labelling predicates given in `predicates.txt` to find labels:

    labelify data.ttl --context supportingVocab.ttl --labels predicates.txt

*By default, only `rdfs:label`, `dcterms:title`, `schema:name` and skos:prefLabel` are used to find labels.*

`predicates.txt` needs to be a list of labelling predicates - one per line and un-prefixed - e.g.:

    http://xmlns.com/foaf/0.1/givenName
    http://example.com/mySpecialLabel
    http://www.w3.org/2008/05/skos-xl#altLabel

Find all the missing labels in the graph `http://example-graph.com` at the sparql endpoint `http://mytriplestore/sparql` 
using basic HTTP auth to connect:

    labelify http://mytriplestore/sparql --graph http://example-graph --username admin

*labelify will prompt for the password or it can be provided with the `--password` flag if you don't mind it being 
saved to your shell's history.*

#### Label Extraction

Get all the IRIs with missing labels from a local RDF file and put them into a text file with one IRI per line:

    labelify all my_file.ttl -r > iris-missing-labels.txt

*note use of `-r` for simple IRI printing*

Use the output file to generate an RDF file containing the labels, extracted from either another RDF file, a directory 
of RDF files or a SPARQL endpoint:

    labelify -x iris-missing-labels.txt other-rdf-file.ttl > labels.ttl
    # or
    labelify -x iris-missing-labels.txt dir-of-rdf-files/ > labels.ttl
    # or
    labelify -x iris-missing-labels.txt http://some-sparql-endpoint.com/sparql > labels.ttl

#### Command line output formats

By default, labelify will print helpful progress and configuration messages and attempt to group the missing labels by 
namespace, making it easier to quickly understand the output.

The `--raw/-r` option can be appended to any of the examples above to tell labelify to only print the uris of objects 
with missing labels (one per line) and no other messages. This is useful for command line composition if you wish to 
pipe the output into another process.

#### More command line options

For more help and the complete list of command line options just run

    labelify --help
    # or 
    labelfy -h

As per unix conventions all the flags shown above can also be used with short codes. i.e. `-g` is the same as `--graph`.

### Python module

Print missing labels for all the objects (not subjects or predicates) in `data.ttl`, taking into account any labels 
which have been defined in RDF files in the `supportingVocabs` directory.

Using `skos:prefLabel` and `rdfs:label`, but not `dcterms:title` and `schema:name` (as per default) as the labelling 
predicates.

```python
from labelify import find_missing_labels
from rdflib import Graph
import glob

data = Graph().parse("tests/manifest.ttl")
context = Graph()

for context_file in glob.glob("tests/one/background/*.ttl"):
    context.parse(context_file)
    
missing_labels = find_missing_labels(
    data,
    context
)
print(missing_labels)
```

And, to extract labels, descriptions & seeAlso details for given IRIs from a given directory of RDF files:

```python
from pathlib import Path
from labelify import extract_labels

iris = Path("tests/get_iris/iris.txt").read_text().splitlines()
lbls = extract_labels(iris, Path("tests/one/background/"))
```

## Development

### Installing from source

Clone the repository and install the dependencies:

*labelify uses [Poetry](https://python-poetry.org/) to manage its dependencies.*

    git clone git@github.com:Kurrawong/labelify.git
    cd labelify
    poetry install

You can then use labelify from the command line

    poetry shell
    python labelify/ ...

### Running tests

    poetry run pytest

Several of the tests require a Fuseki triplestore instance to be available, so you need **Docker** running as the tests 
will attempt to use [testcontainers](https://testcontainers.com/guides/getting-started-with-testcontainers-for-python/) 
to create throwaway containers for this purpose.

### Formatting the codebase

    poetry run black . 

    poetry run ruff check --fix labelify/

## License

[BSD-3-Clause](https://opensource.org/license/bsd-3-clause/). See the LICENSE file in the codebase.

## Contact

**KurrawongAI**  
<info@kurrawong.ai>  
<https://kurrawong.ai>
