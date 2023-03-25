import argparse
import dataclasses
import fnmatch
import os
import sys
from pathlib import Path
from typing import Optional, Set

import tomli

from ._importlib import dist2pkg, machinery


_CWD = os.getcwd()


@dataclasses.dataclass
class Settings:
    search_path: str = _CWD
    exclude: Set[str] = dataclasses.field(default_factory=set)
    packages: Set[str] = dataclasses.field(default_factory=set)
    requirements: Set[str] = dataclasses.field(default_factory=set)
    ignore_modules: Set[str] = dataclasses.field(default_factory=set)
    ignore_packages: Set[str] = dataclasses.field(default_factory=set)
    project_modules: Set[str] = dataclasses.field(default_factory=set)
    report: str = 'table'
    pyproject: Optional[str] = None
    setup: Optional[str] = None
    verbose: int = 0
    quiet: bool = False

    def __post_init__(self):
        self._unanchor_exclude()
        self._locate_project_modules()

    def _unanchor_exclude(self):
        unanchor_exclude = set()
        for i, exclude in enumerate(self.exclude):
            if not exclude.startswith(os.path.sep) and not exclude.startswith('**/'):
                exclude = f'**/{exclude}'
            if exclude.endswith('/'):
                exclude = f'{exclude}**'
            unanchor_exclude.add(exclude)
        self.exclude = unanchor_exclude

    def _locate_project_modules(self):
        if self.pyproject:
            project_name = gather_config(self.pyproject).get('project', {}).get('name', '')
            if project_name and project_name in dist2pkg:
                self.project_modules.update(dist2pkg[project_name])

        if os.path.isfile(self.search_path):
            stem, ext = os.path.splitext(os.path.basename(self.search_path))
            if ext in machinery.SOURCE_SUFFIXES:
                self.project_modules.add(stem)
        elif '__init__.py' in os.listdir(self.search_path):
            self.project_modules.add(os.path.basename(self.search_path))
        else:
            for root, dirs, files in os.walk(self.search_path):
                if any(fnmatch.fnmatch(root, exclude) for exclude in self.exclude):
                    del dirs[:]
                    continue
                if any(f == '__init__.py' for f in files):
                    self.project_modules.add(os.path.basename(root))
                    del dirs[:]
                    continue
                for f in files:
                    full_file = os.path.join(root, f)
                    if not self.exclude or not any(
                        fnmatch.fnmatch(full_file, exclude) for exclude in self.exclude
                    ):
                        stem, ext = os.path.splitext(f)
                        if ext in machinery.SOURCE_SUFFIXES:
                            self.project_modules.add(stem)

    @classmethod
    def from_interactive(cls):
        arguments = CLISettings.parse_args(sys.argv[1:])
        if not hasattr(arguments, 'pyproject'):
            pyproject = Path(getattr(arguments, 'search_path', _CWD)).resolve() / 'pyproject.toml'
            while not pyproject.is_file():
                if pyproject.parent == pyproject.parent.parent:
                    break
                pyproject = pyproject.parent.parent / 'pyproject.toml'
            else:
                arguments.pyproject = pyproject
        elif not arguments.pyproject:
            arguments.pyproject = None
        elif not os.path.isfile(arguments.pyproject):
            raise RuntimeWarning(f'Supplied --pyproject cannot be found: {arguments.pyproject}')

        settings_kwargs = {
            'search_path': _CWD,
            'exclude': set(),
            'packages': set(),
            'requirements': set(),
            'ignore_modules': set(),
            'ignore_packages': set(),
            'project_modules': set(),
            'report': 'table',
            'pyproject': None,
            'setup': None,
            'verbose': 0,
            'quiet': False,
        }
        if pyproject := getattr(arguments, 'pyproject', ''):
            pyproject_kwargs = gather_config(pyproject)
            for kw, setting in pyproject_kwargs.items():
                if isinstance(setting, list):
                    pyproject_kwargs[kw] = set(setting)
            settings_kwargs.update(pyproject_kwargs)
        arg_kwargs = vars(arguments)
        for kw, setting in arg_kwargs.items():
            if isinstance(setting, list):
                arg_kwargs[kw] = set(setting)
        settings_kwargs.update(arg_kwargs)
        return cls(**settings_kwargs)


CLISettings = argparse.ArgumentParser(argument_default=argparse.SUPPRESS)
CLISettings.add_argument(
    '--pyproject',
    help='Path to a pyproject.toml which will be searched for requirements and bonded settings',
)
CLISettings.add_argument(
    '--setup',
    help='Path to a setup.cfg which will be searched for requirements',
)
CLISettings.add_argument(
    '--packages',
    action='extend',
    nargs='+',
    help='Add a package to be checked for',
)
CLISettings.add_argument(
    '-r',
    '--requirements',
    action='append',
    help='Pip-requirements file used to specify further requirements.'
    ' Can be specified multiple times',
)
CLISettings.add_argument(
    '--ignore-modules',
    action='extend',
    nargs='+',
    help='These module will not be reported as missing a package',
)
CLISettings.add_argument(
    '--ignore-packages',
    action='extend',
    nargs='+',
    help='These packages will not be reported as unused',
)
CLISettings.add_argument(
    '--exclude',
    action='append',
    help='A glob that will exclude paths otherwise matched',
)
CLISettings.add_argument('--report', choices=['table', 'extended-table', 'line', 'none'])
CLISettings.add_argument('--verbose', '-v', action='count')
CLISettings.add_argument('--quiet', '-q', action='store_true')
CLISettings.add_argument('search_path', nargs='?')


def gather_config(pyproject):
    with open(pyproject, 'rb') as pypj:
        return tomli.load(pypj).get('tool', {}).get('bonded', {})
