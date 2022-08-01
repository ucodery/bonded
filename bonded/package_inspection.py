from collections import defaultdict
from pathlib import Path

import importlib_metadata as pkg_metadata

import tomli

from packaging import requirements as pkgreq, utils as pkgutil


pkg2dist = pkg_metadata.packages_distributions()
dist2pkg = defaultdict(list)
for pkg, dists in pkg2dist.items():
    for dist in dists:
        dist2pkg[dist].append(pkg)
dist2pkg = dict(dist2pkg)


class Package:
    """Record tracking usage of a package"""

    def __init__(self, package_name):
        self.package_name = package_name
        self.normalized_name = pkgutil.canonicalize_name(package_name)
        try:
            self.modules = dist2pkg[self.normalized_name]
        except KeyError:
            raise ValueError(
                f'Package {package_name} is not installed in this python interpreter'
            ) from None
        metadata = pkg_metadata.distribution(self.normalized_name)
        self.extends = {
            ep.group.split(':')[0].split('.')[0]
            for ep in metadata.entry_points
            if ep.group != 'console_scripts'
        }
        self.executables = {
            ep.name for ep in metadata.entry_points if ep.group == 'console_scripts'
        }

    def __hash__(self):
        return hash(self.normalized_name)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.normalized_name == other.normalized_name


# Sentinal for a package not installed locally
# the package_name argument doesn't matter, it just need to be valid
# names changed to '    ', which is an illegal package name,
# but also not modified by canonicalize_name
NoPackage = Package(next(iter(dist2pkg)))
NoPackage.package_name = NoPackage.normalized_name = '    '
NoPackage.extends = set()
NoPackage.executables = set()


class PackageInspection(dict):
    """Inspect usage of all package requirements by a project"""

    def __init__(self, requirements):
        for req in requirements:
            self[req]

    def __missing__(self, key):
        ckey = pkgutil.canonicalize_name(key)
        if ckey in self:
            return self[ckey]
        try:
            p = Package(key)
        except ValueError:
            p = NoPackage
        self[ckey] = p
        return p

    def update_from_pyproject(self, pyproject_toml):
        """Add all packages found as requirements in the given pyproject.toml"""
        with open(pyproject_toml, 'rb') as pyproject_file:
            pyproject = tomli.load(pyproject_file)
            project = pyproject.get('project', {})

            for dependency in project.get('dependencies', []):
                self[pkgreq.Requirement(dependency).name]

            for optionals in project.get('optional-dependencies', {}).values():
                for optional in optionals:
                    self[pkgreq.Requirement(optional).name]

    def update_from_pip_requirements(self, requirements_file):
        """Add all packages found in the given requirements file"""
        requirements_file = Path(requirements_file)
        with requirements_file.open('r') as requirements:
            for requirement in requirements:
                requirement = requirement.strip()
                if requirement.startswith('#') or requirement.startswith('--'):
                    continue
                if requirement.startswith('-r'):
                    sub_requirement = requirement[2:].strip()
                    self.update_from_pip_requirements(requirements_file.with_name(sub_requirement))
                    continue
                self[pkgreq.Requirement(requirement).name]
