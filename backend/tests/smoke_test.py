def test_import():
    import dalva

    assert hasattr(dalva, "init")
    assert hasattr(dalva, "table")
    assert hasattr(dalva, "Run")
    assert hasattr(dalva, "Table")
    assert hasattr(dalva, "DalvaSchema")
    assert hasattr(dalva, "DalvaError")


def test_version():
    from importlib.metadata import version

    v = version("dalva")
    assert v


def test_cli_entrypoint():
    from importlib.metadata import entry_points

    cli_eps = [ep for ep in entry_points(group="console_scripts") if ep.name == "dalva"]
    assert cli_eps, "dalva console_scripts entry point not found"


if __name__ == "__main__":
    test_import()
    test_version()
    test_cli_entrypoint()
    print("Smoke test passed!")
