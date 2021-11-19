from pathlib import Path

import tomli

from packaging import utils as pkgutil
from provides import provided_modules
from provides.errors import PackageNotFoundError


def clean_requirement(requirement):
    """Return only the name portion of a Python Dependency Specification string

    the name may still be non-normalized
    """
    return (
        requirement
        # the start of any valid version specifier
        .split("=")[0]
        .split("<")[0]
        .split(">")[0]
        .split("~")[0]
        .split("!")[0]
        # this one is poetry only
        .split("^")[0]
        # quoted marker
        .split(";")[0]
        # start of any extras
        .split("[")[0]
        # url spec
        .split("@")[0]
        .strip()
    )


class Package:
    """Record tracking usage of a package"""

    def __init__(self, package_name):
        self.package_name = package_name
        self.normalized_name = pkgutil.canonicalize_name(package_name)
        try:
            self.modules = provided_modules(self.package_name)
            self.found_distribution = True
        except PackageNotFoundError:
            # If the package cannot be found, assume it provides one top level
            # module with the same name as the package
            self.modules = [self.normalized_name.replace("-", "_")]
            self.found_distribution = False

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.normalized_name == other.normalized_name


class PackageInspection(dict):
    """Inspect useage of all package requirements by a project"""

    def __init__(self, requirements):
        for req in requirements:
            self[req]

    def __missing__(self, key):
        p = Package(key)
        self[p.normalized_name] = p
        return p

    def update_from_pyproject(self, pyproject_toml):
        """Add all packages found as requirements in the given pyproject.toml"""
        with open(pyproject_toml, "rb") as pyproject_file:
            pyproject = tomli.load(pyproject_file)
            project = pyproject.get("project", {})

            for dependency in project.get("dependencies", []):
                self[clean_requirement(dependency)]

            optional_dependencies = project.get("optional-dependencies", {})
            for optionals in optional_dependencies.values():
                for optional in optionals:
                    self[clean_requirement(optional)]

    def update_from_pip_requirements(self, requirements_file):
        """Add all packages found in the given requirements file"""
        requirements_file = Path(requirements_file)
        with requirements_file.open("r") as requirements:
            for requirement in requirements:
                requirement = requirement.strip()
                if requirement.startswith("#") or requirement.startswith("--"):
                        continue
                if requirement.startswith("-r"):
                    sub_requirement = requirement[2:].strip()
                    self.update_from_pip_requirements(requirements_file.with_name(sub_requirement))
                    continue
                self[clean_requirement(requirement)]
