from bonded.package_inspection import Package


def test_equivilant_packages():
    bonded = Package("bonded")
    Bonded = Package("Bonded")

    assert bonded == Bonded


def test_loading_self():
    bonded = Package("bonded")

    assert bonded.package_name == "bonded"
    assert bonded.normalized_name == "bonded"
    assert bonded.modules == ["bonded"]
    assert bonded.extends == set()
    assert bonded.executables == set()
