import logging
import tokenize
import warnings

from ._internal import _Record


log = logging.getLogger(__name__)


known_dynamic_loaders = [
    '__import__',
    'import_module',
    'run_module',
    'importorskip',  # pytest helper
]


class Module(_Record):
    """Record tracking modules seen in source code"""

    def __init__(self, module_name):
        super().__init__(module_name)
        self.found_import_stmt = False
        self.found_import_fun = False


class ModuleInspection(dict):
    """Inspect usage of all top-level modules imported by a project"""

    def __missing__(self, key):
        self[key] = Module(key)
        return self[key]

    def inspect_imports(self, project_files):
        """Collect all modules found in the given files"""
        for pfile in project_files:
            try:
                self.find_imports_from_token(pfile)
            except tokenize.TokenError:
                warnings.warn(f'Found {pfile} but cannot parse it.')

    def find_imports_from_token(self, source_module):
        """Return all top level modules that are imported by `source_module`"""
        # TODO:tokens.line
        def add_package_from_statement(token):
            if token.exact_type in (tokenize.DOT, tokenize.ELLIPSIS):
                # don't record relative imports
                return
            assert token.type == tokenize.NAME, 'illegal syntax'
            self[token.string].found_import_stmt = True
            log.debug('Module %s was found imported in %s', token.string, source_module)

        def add_package_from_function(token):
            value = token.string
            while value[0].lower() in ('r', 'b', 'u', 'f'):
                if value[0].lower() == 'f':
                    return
                value = value[1:]
            if (
                len(value) >= 6
                and value[0] == value[1] == value[2] == value[-1] == value[-2] == value[-3]
            ):
                value = value[3:-3]
            else:
                value = value[1:-1]
            if value.startswith('.'):
                # don't record relative imports
                return
            self[value].found_import_fun = True
            log.debug('Module %s was found dynamically imported in %s', token.string, source_module)

        with tokenize.open(source_module) as stream:
            try:
                tokens = tokenize.generate_tokens(stream.readline)
                for token in tokens:
                    if token.type == tokenize.NAME and token.string in (
                        'raise',
                        'yield',
                    ):
                        # consume any use of yield keyword not part of an import statement
                        while not (
                            token.type == tokenize.NEWLINE or token.exact_type == tokenize.SEMI
                        ):
                            token = next(tokens)
                    if token.type == tokenize.NAME and token.string == 'import':
                        token = next(tokens)
                        add_package_from_statement(token)
                        while not (
                            token.type == tokenize.NEWLINE or token.exact_type == tokenize.SEMI
                        ):
                            token = next(tokens)
                            if token.exact_type == tokenize.COMMA:
                                token = next(tokens)
                                add_package_from_statement(token)
                    if token.type == tokenize.NAME and token.string == 'from':
                        token = next(tokens)
                        if token.exact_type == tokenize.LPAR:
                            token = next(tokens)
                        add_package_from_statement(token)
                        while not (
                            token.type == tokenize.NEWLINE or token.exact_type == tokenize.SEMI
                        ):
                            # multiple top level packages cannot be imported under a single 'from'
                            # but there may be an 'import' keyword that shouldn't go to the next if
                            token = next(tokens)
                    if token.type == tokenize.NAME and token.string in (known_dynamic_loaders):
                        try:
                            token = next(tokens)
                            if token.exact_type == tokenize.LPAR:
                                token = next(tokens)
                                while not (
                                    token.type == tokenize.NEWLINE
                                    or token.exact_type == tokenize.SEMI
                                ):
                                    if token.type == tokenize.STRING:
                                        followon_token = next(tokens)
                                        if not (
                                            followon_token.type == tokenize.OP
                                            and followon_token.exact_type
                                            not in (tokenize.COMMA, tokenize.RPAR)
                                        ):
                                            add_package_from_function(token)
                                            break
                                        # else not a constant string literal
                                    token = next(tokens)
                        except StopIteration:
                            # this is not necessarily a SyntaxError, as these are not keywords
                            pass
            except (AssertionError, StopIteration) as err:
                # If StopIteration is raised, this file contains illegal syntax
                # This would cause a SyntaxError if run, but caller is already
                # expecting TokenError
                raise tokenize.TokenError from err
