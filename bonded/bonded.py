import tokenize
import re
import warnings
from enum import IntEnum
from pathlib import Path

from packaging import utils as pkgutil
from provides import provided_modules
from provides.errors import PackageNotFoundError


class Confidence(IntEnum):
    VERY_LOW = 5
    LOW = 10
    MEDIUM = 15
    HIGH = 20
    VERY_HIGH = 25


class ModuleInspection:
    """Record tracking modules seen in source code"""
    def __init__(self, module_name, package_search):
        self.module_name = module_name
        self.package = package_search
        self.found_import_stmt = False
        self.found_import_fun = False

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.module_name == other.module_name and self.package == other.package


class PackageInspection:
    """Record tracking usage of a package"""

    def __init__(self, package_name):
        self.package_name = package_name
        self.normalized_name = pkgutil.canonicalize_name(package_name)
        try:
            self.modules = [ModuleInspection(p, self) for p in provided_modules(self.package_name)]
            self.found_distribution = True
        except PackageNotFoundError:
            # If the package cannot be found, assume it provides one top level
            # module with the same name as the package
            self.modules = [ModuleInspection(self.normalized_name.replace("-", "_"), self)]
            self.found_distribution = False

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.normalized_name == other.normalized_name


class Inspection:
    """Record tracking use of requirements by python code"""

    def __init__(self, requirements):
        self.packages = []
        self.module_lookup = {}
        for req in requirements:
            self.packages.append(PackageInspection(req))
            for module in self.packages[-1].modules:
                if module.module_name in self.module_lookup:
                    warnings.warn(
                        f"Top level module {module.module_name} is provided by {module.package.package_name} but is "
                        f"already being searched for under {self.module_lookup[module.module_name].package.package_name}"
                    )
                else:
                    self.module_lookup[module.module_name] = module


def inspect_imports(project_files, given_requirements):
    """Return any items in `given_requirements` that are not used by the given project

    given_requirements: a list of package names
    """
    inspection = Inspection(given_requirements)

    for pfile in project_files:
        try:
            for found_import, found_type in find_imports_from_token(pfile).items():
                if found_import in inspection.module_lookup:
                    if found_type == "statement":
                        inspection.module_lookup[found_import].found_import_stmt = True
        except tokenize.TokenError:
            warnings.warn(f"Found {pfile} but cannot parse it.")
    return inspection


def find_imports_from_token(source_module):
    """Return all top level modules that are imported by `source_module`"""
    found_packages = dict() #TODO:tokens.line
    def add_package_from_statement(token):
        if token.exact_type in (tokenize.DOT, tokenize.ELLIPSIS):
            # don't record relative imports
            return
        assert token.type == tokenize.NAME, "illegal syntax"
        found_packages[token.string] = "statement"

    def add_package_from_function(token):
        value = token.string
        if len(value) >= 6 and value[0] == value[1] == value[2] == value[-1] == value[-2] == value[-3]:
            value = value[3:-3]
        else:
            value = value[1:-1]
        if value.startswith('.'):
            # don't record relative imports
            return
        if value not in found_packages or found_packages[value] != "statement":
            found_packages[value] = "function"

    with tokenize.open(source_module) as stream:
        try:
            tokens = tokenize.generate_tokens(stream.readline)
            for token in tokens:
                if token.type == tokenize.NAME and token.string in ('raise', 'yield'):
                    # consume any use of yield keyword not part of an import statement
                    while not (token.type == tokenize.NEWLINE or token.exact_type == tokenize.SEMI):
                        token = next(tokens)
                if token.type == tokenize.NAME and token.string == 'import':
                    token = next(tokens)
                    add_package_from_statement(token)
                    while not (token.type == tokenize.NEWLINE or token.exact_type == tokenize.SEMI):
                        token = next(tokens)
                        if token.exact_type == tokenize.COMMA:
                            token = next(tokens)
                            add_package_from_statement(token)
                if token.type == tokenize.NAME and token.string == 'from':
                    token = next(tokens)
                    if token.exact_type == tokenize.LPAR:
                        token = next(tokens)
                    add_package_from_statement(token)
                    while not (token.type == tokenize.NEWLINE or token.exact_type == tokenize.SEMI):
                        # multiple top level packages cannot be imported under a single 'from'
                        # but there may be an 'import' keyword that shouldn't trigger the other if
                        token = next(tokens)
                if token.type == tokenize.NAME and token.string in ('__import__', 'import_module', 'run_module'):
                    try:
                        token = next(tokens)
                        if token.exact_type == tokenize.LPAR:
                            token = next(tokens)
                            if token.type == tokenize.STRING:
                                add_package_from_function(token)
                    except StopIteration:
                        # this is not necessarily a SyntaxError, as these are not keywords
                        pass
        except (AssertionError, StopIteration) as err:
            # If StopIteration is raised, this file contains illegal syntax
            # This would cause a SyntaxError if run, but caller is already
            # expecting TokenError
            raise tokenize.TokenError from err

    return found_packages


def iter_source_files(starting_dir, excludes):
    exclude_patterns = [re.compile(exclude) for exclude in excludes]

    for path in Path(starting_dir).rglob('*.py'):
        spath = str(path)
        for exclude in exclude_patterns:
            if exclude.match(spath) is not None:
                break
        else:
            yield path
