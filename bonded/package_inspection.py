import importlib.metadata as pkg_metadata
import itertools
import re
from pathlib import Path

import tomli

from packaging import utils as pkgutil
from provides import Package as Provides
from provides.errors import PackageNotFoundError

def detect_file_type(file_path, first_line):
    executor = ""
    if first_line:
        if first_line.startswith("#!"):
            first_line = first_line[2:].strip()
            shebang = first_line.split()
            if len(shebang) > 1 and (shebang[0] == "env" or shebang[0].endswith("/env")):
                shebang.pop(0)
            executor = shebang[0].rsplit("/")[-1]

    if (file_path.suffix in ["py",]
        or executor in ["python", "python2", "python3"]
    ):
        return "python"
    if (file_path.suffix in ["sh", "bash", "zsh", "fish", "xosh"]
        or executor in ["sh", "bash", "zsh", "fish", "xosh"]
    ):
        return "shell"
    if file_path.suffix in ["ini", "cfg"]:
        return "ini"
    if file_path.suffix in ["yaml", "yml"]:
        return "yaml"

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
            self.modules = pkg_metadata.packages_distributions()[self.normalized_name]
        except KeyError:
            raise ValueError(f"Package {package_name} is not installed in this python interpreter")
        # NOTE it would be *really* nice if EntryPoints both recorded which package an entry point came from originally
        # and provided a flat way to iterate over them...
        # value like 'setuptools.dist:check_entry_points', group like 'distutils.setup_keywords'
        self.extends = {
            ep.group.split('.')[0]
            for ep in itertools.chain.from_iterable(pkg_metadata.entry_points().values())
            if ep.value.split('.')[0] == self.normalized_name and ep.group != 'console_scripts'
        }
        self.executables = {
            ep.name
            for ep in pkg_metadata.entry_points(group='console_scripts')
            if ep.value.split('.')[0] == self.normalized_name
        }


    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.normalized_name == other.normalized_name


class PackageInspection(dict):
    """Inspect usage of all package requirements by a project"""

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

    def inspect_executables(self, project_files):
        #TODO: python -m but only after finding __main__.py
        # re.compile(fr"\bpython[\d.]*\s+-m\s+{exe}\b")
        exe_searches = {exe: (pkg, re.compile(fr"\b{exe}\b"))
                              for pkg in self.values() for exe in pkg.executables}
        for project_file in project_files:
            pfile = project_file.read_text().splitlines()
            if not pfile:
                continue

            file_type = detect_file_type(project_file.name, pfile[0])

            for number, line in enumerate(pfile):
                for exe in exe_searches:
                    if exe_searches[exe][1].search(line):
                        self[exe_searches[exe][0]].executables[exe] = (file_type, str(project_file), number)
