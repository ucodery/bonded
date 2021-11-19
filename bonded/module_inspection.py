import tokenize
import warnings


class Module:
    """Record tracking modules seen in source code"""
    def __init__(self, module_name):
        self.module_name = module_name
        self.found_import_stmt = False
        self.found_import_fun = False

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.module_name == other.module_name


class ModuleInspection(dict):
    """Inspect useage of all top-level modules imported by a project"""

    def __missing__(self, key):
        self[key] = Module(key)
        return self[key]


    def inspect_imports(self, project_files):
        """Collect all modules found in the given files"""
        for pfile in project_files:
            try:
                self.find_imports_from_token(pfile)
            except tokenize.TokenError:
                warnings.warn(f"Found {pfile} but cannot parse it.")


    def find_imports_from_token(self, source_module):
        """Return all top level modules that are imported by `source_module`"""
        #TODO:tokens.line
        def add_package_from_statement(token):
            if token.exact_type in (tokenize.DOT, tokenize.ELLIPSIS):
                # don't record relative imports
                return
            assert token.type == tokenize.NAME, "illegal syntax"
            self[token.string].found_import_stmt = True

        def add_package_from_function(token):
            value = token.string
            if len(value) >= 6 and value[0] == value[1] == value[2] == value[-1] == value[-2] == value[-3]:
                value = value[3:-3]
            else:
                value = value[1:-1]
            if value.startswith('.'):
                # don't record relative imports
                return
            self[value].found_import_fun = True

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
