import logging
import re
from collections import namedtuple

from ._internal import _Record


log = logging.getLogger(__name__)


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


_CallingFile = namedtuple('_CallingFile', ['file_name', 'file_type', 'line_number'])


class Executable(_Record):
    """Record tracking usage of an executable"""

    def __init__(self, executable_name):
        super().__init__(executable_name)
        self.found_executions = set()


class ExecutableInspection(dict):
    """Inspect usage of executables"""

    def __init__(self, keys):
        instanciated_args = ((a, Executable(a)) for a in keys)
        super().__init__(instanciated_args)

    def inspect_executables(self, project_files):
        # TODO: python -m but only after finding __main__.py
        # re.compile(fr"\bpython[\d.]*\s+-m\s+{exe}\b")
        exe_searches = {
            exe.name: re.compile(rb'\b%b\b' % exe.name.encode('utf-8')) for exe in self.values()
        }
        for project_file in project_files:
            if not project_file.is_file():
                continue
            pfile = project_file.read_bytes().splitlines()
            if not pfile:
                continue

            file_type = detect_file_type(project_file, pfile[0])

            for lineno, line in enumerate(pfile, start=1):
                for exe, search in exe_searches.items():
                    if search.search(line):
                        self[exe].found_executions.add(
                            _CallingFile(project_file.name, file_type, lineno)
                        )
                        log.debug('Found executable %s in %s:%s', exe, project_file, lineno)
