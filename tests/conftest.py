from pathlib import Path

import pytest
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs

FUSEKI_IMAGE = "ghcr.io/kurrawong/fuseki-geosparql:git-main-e642d849"


@pytest.fixture(scope="module")
def fuseki_container(request: pytest.FixtureRequest):
    container = DockerContainer(FUSEKI_IMAGE)
    container.with_volume_mapping(
        str(Path(__file__).parent / "shiro.ini"), "/fuseki/shiro.ini"
    )
    container.with_volume_mapping(
        str(Path(__file__).parent / "config.ttl"), "/fuseki/config.ttl"
    )
    container.with_exposed_ports(3030)
    container.start()
    wait_for_logs(container, "Started")

    def cleanup():
        container.stop()

    request.addfinalizer(cleanup)
    return container
