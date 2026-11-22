import project_name


def test_version() -> None:
    assert len(project_name.__version__.split(".")) == 3
