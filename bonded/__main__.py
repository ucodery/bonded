import fnmatch
import logging
import os.path
import sys
from pathlib import Path

import rich.logging

from .display import display_closing, display_report
from .evaluation import evaluate_bonds

from .executable_inspection import ExecutableInspection
from .module_inspection import ModuleInspection
from .package_inspection import PackageInspection
from .settings import Settings


log = logging.getLogger('bonded')


def setup_logging(level):
    if level < 1:
        return
    elif level > 5:
        level = 5

    lvl = [logging.CRITICAL, logging.ERROR, logging.WARN, logging.INFO, logging.DEBUG][level - 1]
    log.addHandler(rich.logging.RichHandler(level=lvl))
    log.setLevel(lvl)


def iter_source_files(starting_dir, excludes, file_pattern):
    for i, exclude in enumerate(excludes):
        if not exclude.startswith(os.path.sep) and not exclude.startswith('**/'):
            excludes[i] = f'**/{exclude}'

    for path in Path(starting_dir).rglob(file_pattern):
        spath = str(path)
        if not excludes or not any(fnmatch.fnmatch(spath, exclude) for exclude in excludes):
            yield path


def main():
    settings = Settings.from_interactive()

    setup_logging(settings.verbose)

    all_files = iter_source_files(settings.search_path, settings.exclude, '*')
    python_files = iter_source_files(settings.search_path, settings.exclude, '*.py')

    packages = PackageInspection(settings.packages)
    if settings.pyproject:
        packages.update_from_pyproject(settings.pyproject)
    if settings.setup:
        packages.update_from_setup(settings.setup)
    for pip_requirements in settings.requirements:
        packages.update_from_pip_requirements(pip_requirements)

    modules = ModuleInspection()
    modules.inspect_imports(python_files)

    executables = ExecutableInspection((e for p in packages.values() for e in p.executables))
    executables.inspect_executables(all_files)

    report = evaluate_bonds(settings, modules, packages, executables)

    display_report(settings, report)
    display_closing(settings, report)
    return 0 if report.passes() else 1


if __name__ == '__main__':
    sys.exit(main())
