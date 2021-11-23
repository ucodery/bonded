import argparse
import dataclasses
import os
from typing import List

import tomli

@dataclasses.dataclass
class Settings:
    search_path: str
    exclude: List[str]
    packages: List[str]
    requirements: List[str]
    pyproject: str
    verbose: bool
    quiet: bool

    @property
    def project_modules(self):
        modules = [os.path.basename(os.path.realpath(self.search_path))]
        return modules


def gather_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--packages", default="")
    parser.add_argument("-r", "--requirements", action="append", default=[])
    parser.add_argument("--pyproject", default="")
    parser.add_argument("--exclude", action="append", help="A regular expression that will exclude paths otherwise matched", default=[])
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("search_path", nargs="?", default=os.getcwd())
    args = parser.parse_args()

    args.packages = args.packages.replace(",", " ").split()

    return args


def gather_config(pyproject):
    with open(pyproject, "rb") as pypj:
        return tomli.load(pypj).get("tool", {}).get("bonded", {})
