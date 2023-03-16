import logging
import os
import stat
import sysconfig
from configparser import ConfigParser
from pathlib import Path

import tomli

from packaging import requirements as pkgreq, utils as pkgutil

from ._importlib import dist2pkg, metadata as pkg_metadata
from ._internal import _Record


log = logging.getLogger(__name__)


class Package(_Record):
    """Record tracking usage of a package"""

    @staticmethod
    def _normalize_name(name):
        return pkgutil.canonicalize_name(name)

    def _executable_files(self):
        """Return executable files provided by this package"""
        for fname in pkg_metadata.files(self.package_name):
            # this is the only path that is sure to be on PATH
            # it is spelled with '/' on all platforms
            fname = str(fname)
            if fname.startswith('../../../bin/'):
                exe_name = fname[13:]
                fs_path = os.path.join(sysconfig.get_path('purelib'), fname)
                if (
                    exe_name
                    and '/' not in exe_name
                    and os.path.isfile(fs_path)
                    and (os.stat(fs_path).st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))
                ):
                    yield exe_name

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
            self.executables.update(exe for exe in self._executable_files())
            log.debug('Package %s was associated with modules %s', self.package_name, self.modules)
            log.debug(
                'Package %s was associated with extensions %s', self.package_name, self.extends
            )
            log.debug(
                'Package %s was associated with executables %s', self.package_name, self.executables
            )
        else:
            self.installed = False
            self.modules = []
            self.extends = set()
            self.executables = set()
            log.debug('Package %s is not installed', self.package_name)
        self.markers = []


class PackageInspection(dict):
    """Inspect usage of all package requirements by a project"""

    def __init__(self, requirements):
        for req in requirements:
            self._add_from_requirement(req)

    def __missing__(self, key):
        ckey = pkgutil.canonicalize_name(key)
        if ckey not in self:
            self[ckey] = Package(key)
        return self[ckey]

    def _add_from_requirement(self, requirement):
        parsed = pkgreq.Requirement(requirement)
        self[parsed.name]
        if parsed.marker:
            self[parsed.name].markers.append(parsed.marker)

    def update_from_pyproject(self, pyproject_toml):
        """Add all packages found as requirements in the given pyproject.toml"""
        with open(pyproject_toml, 'rb') as pyproject_file:
            pyproject = tomli.load(pyproject_file)
            project = pyproject.get('project', {})

            for dependency in project.get('dependencies', []):
                log.info(
                    'Found dependency %s in %s project.dependencies', dependency, pyproject_toml
                )
                self._add_from_requirement(dependency)

            for opt_name, optionals in project.get('optional-dependencies', {}).items():
                for optional in optionals:
                    log.info(
                        'Found dependency %s in %s project.optional-dependencies.%s',
                        optional,
                        pyproject_toml,
                        opt_name,
                    )
                    self._add_from_requirement(optional)
            for dependency in pyproject.get('build-system', {}).get('requires', []):
                log.info(
                    'Found dependency %s in %s build-system.requires', dependency, pyproject_toml
                )
                self._add_from_requirement(dependency)

    def update_from_pip_requirements(self, requirements_file):
        """Add all packages found in the given requirements file"""
        requirements_file = Path(requirements_file)
        with requirements_file.open('r') as requirements:
            for requirement in requirements:
                requirement = requirement.strip()
                if requirement.startswith('-r') or requirement.startswith('--requirements'):
                    sub_requirement = requirement.split()[1].strip()
                    self.update_from_pip_requirements(requirements_file.parent / sub_requirement)
                    continue
                if not requirement or requirement.startswith('#') or requirement.startswith('-'):
                    continue
                log.info('Found requirement %s in %s', requirement, requirements_file.name)
                self._add_from_requirement(requirement)

    def update_from_setup(self, setup_cfg):
        """Add all packages found in the given setup.cfg file"""
        setup = ConfigParser()
        setup.read(setup_cfg)
        for requirement in setup.get('options', 'install_requires', fallback='').splitlines():
            if requirement:
                log.info('Found requirement %s in %s [options]', requirement, setup_cfg)
                self._add_from_requirement(requirement)
        if 'options.extras_require' in setup:
            for requirements in setup['options.extras_require'].values():
                for requirement in requirements.splitlines():
                    if requirement:
                        log.info(
                            'Found requirement %s in %s [options.extras_require]',
                            requirement,
                            setup_cfg,
                        )
                        self._add_from_requirement(requirement)
