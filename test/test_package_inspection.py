from bonded.package_inspection import Package


def test_uninstalled_package():
    # illegal package name, so will never be installed
    uninstalled = Package('    ')

    assert uninstalled.package_name == '    '
    assert uninstalled.name == '    '
    assert uninstalled.modules == []
    assert uninstalled.extends == set()
    assert uninstalled.executables == set()


def test_equivilant_packages():
    bonded = Package('bonded')
    Bonded = Package('Bonded')

    assert bonded is Bonded


def test_loading_self():
    bonded = Package('bonded')

    assert bonded.package_name == 'bonded'
    assert bonded.name == 'bonded'
    assert bonded.modules == ['bonded']
    assert bonded.extends == set()
    assert bonded.executables == {'bonded'}
