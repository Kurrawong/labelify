import subprocess


def test_cmd_input_valid():
    p = subprocess.Popen(
        [
            "labelify",
            "-c",
            "tests/one/background",
            "tests/one/data-access-rights.ttl",
            "-s",
            "true",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    err = ""
    while p.poll() is None:
        err += p.stderr.readline().decode()

    assert err == ""


def test_cmd_input_invalid():
    p = subprocess.Popen(
        [
            "labelify",
            "-c",
            "tests/one/background test/one/data-access-rights",
            "-s",
            "true",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    err = ""
    while p.poll() is None:
        err += p.stderr.readline().decode()

    assert "Must be a file, folder or sparql endpoint" in err


def test_cmd_context_invalid():
    p = subprocess.Popen(
        [
            "labelify",
            "-c",
            "tests/one/backgroundx test/one/data-access-rights.ttl",
            "-s",
            "true",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    err = ""
    while p.poll() is None:
        err += p.stderr.readline().decode()

    assert "Must be a file, folder or sparql endpoint" in err


def test_nodetype_all():
    """Checks that tet case one, with labels set to skos:prefLabel and sdo:name, has 31 results"""
    with subprocess.Popen(
        [
            "labelify",
            "-c",
            "tests/one/background",
            "tests/one/data-access-rights.ttl",
            "-r",
        ],
        stdout=subprocess.PIPE,
    ) as proc:
        result = []
        while proc.poll() is None:
            line = proc.stdout.readline().strip().decode()
            if line.startswith("http"):
                result.append(line)

        assert len(result) == 0


def test_x():
    with subprocess.Popen(
        [
            "labelify",
            "-c",
            "tests/one/background",
            "tests/one/data-access-rights.ttl",
            "-l",
            "http://www.w3.org/2004/02/skos/core#prefLabel,https://schema.org/name",
        ],
        stdout=subprocess.PIPE,
    ) as proc:
        result = ""
        while proc.poll() is None:
            result += proc.stdout.readline().decode()


def test_getlabels():
    p = subprocess.Popen(
        [
            "labelify",
            "-g",
            "tests/get_iris/iris.txt",
            "tests/one/background/",
            "-s",
            "true",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    err = ""
    while p.poll() is None:
        err += p.stderr.readline().decode()

    assert err == ""
