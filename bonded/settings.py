import argparse
import dataclasses
import logging
import os
from pathlib import Path
from typing import List, Optional

import tomli


log = logging.getLogger(__name__)


@dataclasses.dataclass
class Settings:
    search_path: str
    exclude: List[str]
    packages: List[str]
    requirements: List[str]
    ignore_modules: List[str]
    ignore_packages: List[str]
    report: List[str]
    pyproject: Optional[str]
    setup: Optional[str]
    verbose: int
    quiet: bool

    @property
    def project_modules(self):
        modules = [os.path.basename(os.path.realpath(self.search_path))]
        return modules

    @classmethod
    def from_interactive(cls):
        arguments = gather_args()
        if arguments.pyproject is None:
            pyproject = Path(arguments.search_path).resolve() / 'pyproject.toml'
            while not pyproject.is_file():
                if pyproject.parent == pyproject.parent.parent:
                    log.warn('Could not find a pyproject.toml')
                    break
                pyproject = pyproject.parent.parent / 'pyproject.toml'
            else:
                arguments.pyproject = pyproject
        elif arguments.pyproject:
            if not os.path.isfile(arguments.pyproject):
                raise RuntimeWarning(f'Supplied --pyproject cannot be found: {arguments.pyproject}')

        settings_kwargs = vars(arguments)
        if arguments.pyproject:
            settings_kwargs.update(gather_config(arguments.pyproject))

        return cls(**settings_kwargs)


def gather_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--packages',
        action='extend',
        nargs='+',
        help='Add a package to be checked for',
        default=[],
    )
    parser.add_argument('-r', '--requirements', action='append', default=[])
    parser.add_argument('--pyproject', default=None)
    parser.add_argument(
        '--setup', help='Path to a setup.cfg which will be searched for requirements', default=None
    )
    parser.add_argument(
        '--exclude',
        action='append',
        help='A glob that will exclude paths otherwise matched',
        default=[],
    )
    parser.add_argument(
        '--ignore-modules',
        action='extend',
        nargs='+',
        help='These module will not be reported as missing a package',
        default=[],
    )
    parser.add_argument(
        '--ignore-packages',
        action='extend',
        nargs='+',
        help='These packages will not be reported as unused',
        default=[],
    )
    parser.add_argument(
        '--report', choices=['table', 'extended-table', 'line', 'none'], default='table'
    )
    parser.add_argument('--verbose', '-v', action='count', default=0)
    parser.add_argument('--quiet', '-q', action='store_true')
    parser.add_argument('search_path', nargs='?', default=os.getcwd())
    args = parser.parse_args()
    return args


def gather_config(pyproject):
    with open(pyproject, 'rb') as pypj:
        return tomli.load(pypj).get('tool', {}).get('bonded', {})
