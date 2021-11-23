try:
    # more complete, but 3.10+
    from sys import stdlib_module_names
except ImportError:
    # from python3.9
    stdlib_module_names = {
        '__future__', '_abc', '_aix_support', '_ast', '_asyncio', '_bisect', '_blake2',
        '_bootsubprocess', '_bz2', '_codecs', '_codecs_cn', '_codecs_hk', '_codecs_iso2022',
        '_codecs_jp', '_codecs_kr', '_codecs_tw', '_collections', '_collections_abc',
        '_compat_pickle', '_compression', '_contextvars', '_crypt', '_csv', '_ctypes', '_curses',
        '_curses_panel', '_datetime', '_dbm', '_decimal', '_elementtree', '_frozen_importlib',
        '_frozen_importlib_external', '_functools', '_gdbm', '_hashlib', '_heapq', '_imp', '_io',
        '_json', '_locale', '_lsprof', '_lzma', '_markupbase', '_md5', '_msi', '_multibytecodec',
        '_multiprocessing', '_opcode', '_operator', '_osx_support', '_overlapped', '_pickle',
        '_posixshmem', '_posixsubprocess', '_py_abc', '_pydecimal', '_pyio', '_queue', '_random',
        '_sha1', '_sha256', '_sha3', '_sha512', '_signal', '_sitebuiltins', '_socket', '_sqlite3',
        '_sre', '_ssl', '_stat', '_statistics', '_string', '_strptime', '_struct', '_symtable',
        '_thread', '_threading_local', '_tkinter', '_tracemalloc', '_uuid', '_warnings', '_weakref',
        '_weakrefset', '_winapi', '_zoneinfo', 'abc', 'aifc', 'antigravity', 'argparse', 'array',
        'ast', 'asynchat', 'asyncio', 'asyncore', 'atexit', 'audioop', 'base64', 'bdb', 'binascii',
        'binhex', 'bisect', 'builtins', 'bz2', 'cProfile', 'calendar', 'cgi', 'cgitb', 'chunk',
        'cmath', 'cmd', 'code', 'codecs', 'codeop', 'collections', 'colorsys', 'compileall',
        'concurrent', 'configparser', 'contextlib', 'contextvars', 'copy', 'copyreg', 'crypt',
        'csv', 'ctypes', 'curses', 'dataclasses', 'datetime', 'dbm', 'decimal', 'difflib', 'dis',
        'distutils', 'doctest', 'email', 'encodings', 'ensurepip', 'enum', 'errno', 'faulthandler',
        'fcntl', 'filecmp', 'fileinput', 'fnmatch', 'formatter', 'fractions', 'ftplib', 'functools',
        'gc', 'genericpath', 'getopt', 'getpass', 'gettext', 'glob', 'graphlib', 'grp', 'gzip',
        'hashlib', 'heapq', 'hmac', 'html', 'http', 'idlelib', 'imaplib', 'imghdr', 'imp',
        'importlib', 'inspect', 'io', 'ipaddress', 'itertools', 'json', 'keyword', 'lib2to3',
        'linecache', 'locale', 'logging', 'lzma', 'mailbox', 'mailcap', 'marshal', 'math',
        'mimetypes', 'mmap', 'modulefinder', 'msilib', 'msvcrt', 'multiprocessing', 'netrc', 'nis',
        'nntplib', 'nt', 'ntpath', 'nturl2path', 'numbers', 'opcode', 'operator', 'optparse', 'os',
        'ossaudiodev', 'parser', 'pathlib', 'pdb', 'pickle', 'pickletools', 'pipes', 'pkgutil',
        'platform', 'plistlib', 'poplib', 'posix', 'posixpath', 'pprint', 'profile', 'pstats',
        'pty', 'pwd', 'py_compile', 'pyclbr', 'pydoc', 'pydoc_data', 'pyexpat', 'queue', 'quopri',
        'random', 're', 'readline', 'reprlib', 'resource', 'rlcompleter', 'runpy', 'sched',
        'secrets', 'select', 'selectors', 'shelve', 'shlex', 'shutil', 'signal', 'site', 'smtpd',
        'smtplib', 'sndhdr', 'socket', 'socketserver', 'spwd', 'sqlite3', 'sre_compile',
        'sre_constants', 'sre_parse', 'ssl', 'stat', 'statistics', 'string', 'stringprep', 'struct',
        'subprocess', 'sunau', 'symtable', 'sys', 'sysconfig', 'syslog', 'tabnanny', 'tarfile',
        'telnetlib', 'tempfile', 'termios', 'textwrap', 'this', 'threading', 'time', 'timeit',
        'tkinter', 'token', 'tokenize', 'trace', 'traceback', 'tracemalloc', 'tty', 'turtle',
        'turtledemo', 'types', 'typing', 'unicodedata', 'unittest', 'urllib', 'uu', 'uuid', 'venv',
        'warnings', 'wave', 'weakref', 'webbrowser', 'winreg', 'winsound', 'wsgiref', 'xdrlib',
        'xml', 'xmlrpc', 'zipapp', 'zipfile', 'zipimport', 'zlib', 'zoneinfo'
    }
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

    def iter_3rd_party(self, skip_modules=None):
        for module_name in self:
            if (module_name not in stdlib_module_names
                and (skip_modules and module_name not in skip_modules)
            ):
                yield module_name

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
            while value[0].lower() in ('r', 'b', 'u', 'f'):
                if value[0].lower() == 'f':
                    return
                value = value[1:]
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
                                    followon_token = next(tokens)
                                    if not (followon_token.type == tokenize.OP
                                        and not followon_token.exact_type in (tokenize.COMMA, tokenize.RPAR)
                                    ):
                                        add_package_from_function(token)
                                    # else not a constant string literal
                        except StopIteration:
                            # this is not necessarily a SyntaxError, as these are not keywords
                            pass
            except (AssertionError, StopIteration) as err:
                # If StopIteration is raised, this file contains illegal syntax
                # This would cause a SyntaxError if run, but caller is already
                # expecting TokenError
                raise tokenize.TokenError from err
