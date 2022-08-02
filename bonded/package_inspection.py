from collections import defaultdict
from pathlib import Path

import importlib_metadata as pkg_metadata

import tomli

from packaging import requirements as pkgreq, utils as pkgutil

from ._internal import _Record


pkg2dist = pkg_metadata.packages_distributions()
dist2pkg = defaultdict(list)
for pkg, dists in pkg2dist.items():
    for dist in dists:
        dist2pkg[dist].append(pkg)
dist2pkg = dict(dist2pkg)


class Package(_Record):
    """Record tracking usage of a package"""

    @staticmethod
    def _normalize_name(name):
        return pkgutil.canonicalize_name(name)

    def __init__(self, package_name):
        super().__init__(package_name)
        self.package_name = package_name
        if self.name in dist2pkg:
            self.installed = True
            self.modules = dist2pkg[self.name]
            metadata = pkg_metadata.distribution(self.name)
            self.extends = {
                ep.group.split(':')[0].split('.')[0]
                for ep in metadata.entry_points
                if ep.group != 'console_scripts'
            }
            self.executables = {
                ep.name for ep in metadata.entry_points if ep.group == 'console_scripts'
            }
        else:
            self.installed = False
            self.modules = []
            self.extends = set()
            self.executables = set()


class PackageInspection(dict):
    """Inspect usage of all package requirements by a project"""

    def __init__(self, requirements):
        for req in requirements:
            self[req]

    def __missing__(self, key):
        ckey = pkgutil.canonicalize_name(key)
        if ckey not in self:
            self[ckey] = Package(key)
        return self[ckey]

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
