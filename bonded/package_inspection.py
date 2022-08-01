import re
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


def detect_file_type(file_path, first_line):
    executor = ''
    if first_line:
        if first_line.startswith(b'#!'):
            first_line = first_line[2:].strip()
            shebang = first_line.split()
            if len(shebang) > 1 and (shebang[0] == b'env' or shebang[0].endswith(b'/env')):
                shebang.pop(0)
            executor = shebang[0].rsplit(b'/')[-1]

    if file_path.suffix in [
        'py',
    ] or executor in ['python', 'python2', 'python3']:
        return 'python'
    if file_path.suffix in [
        'sh',
        'bash',
        'zsh',
        'fish',
        'xosh',
    ] or executor in ['sh', 'bash', 'zsh', 'fish', 'xosh']:
        return 'shell'
    if file_path.suffix in ['ini', 'cfg']:
        return 'ini'
    if file_path.suffix in ['yaml', 'yml']:
        return 'yaml'


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
        # TODO: executables should be their own inspection, like modules, with confidence levels
        self.executables = {
            ep.name: False for ep in metadata.entry_points if ep.group == 'console_scripts'
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
NoPackage.executables = {}


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

    def inspect_executables(self, project_files):
        # TODO: python -m but only after finding __main__.py
        # re.compile(fr"\bpython[\d.]*\s+-m\s+{exe}\b")
        exe_searches = {
            exe: (pkg, re.compile(rb'\b%b\b' % exe.encode('utf-8')))
            for pkg in self.values()
            for exe in pkg.executables
        }
        for project_file in project_files:
            if not project_file.is_file():
                continue
            pfile = project_file.read_bytes().splitlines()
            if not pfile:
                continue

            # file_type = detect_file_type(project_file, pfile[0])

            for line in pfile:
                for exe, (pkg, search) in exe_searches.items():
                    if search.search(line):
                        pkg.executables[exe] = True
