import tomli
from packaging import utils as pkgutil


def extract_package_name(requirement):
    """Return the normalized package name contained in a requirement string"""
    package = (requirement
        # the start of any valid version specifier
        .split("=")[0]
        .split("<")[0]
        .split(">")[0]
        .split("~")[0]
        .split("!")[0]
        # this one is poetry only
        .split("^")[0]
        .strip()
    )
    return pkgutil.canonicalize_name(package)


def from_string(requirements_string):
    requirements = []
    for package in requirements_string.replace(",", " ").split():
        requirements.append(extract_package_name(package))
    return requirements


def from_pip_requirements(requirements_files):
    """return a list of requirements from all pip-style retuiremetns.txt files given"""
    requirements = []
    for requirements_file in requirements_files:
        with open(requirements_file) as req_file:
            requirements.extend(extract_package_name(r) for r in req_file.readlines())
    return requirements


def from_pyproject(pyproject_toml):
    """return a list of requirements from a project's pyproject.toml"""
    requirements = []
    with open(pyproject_toml, "rb") as pyproject_file:
        pyproject = tomli.load(pyproject_file)
        project = pyproject.get("project", {})
        dependencies = project.get("dependencies", [])
        requirements.extend(extract_package_name(d) for d in dependencies)
        optional_dependencies = project.get("optional-dependencies", {})
        for optionals in optional_dependencies.values():
            requirements.extend(extract_package_name(o) for o in optionals)
    return requirements
