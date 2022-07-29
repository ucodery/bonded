import re
import warnings
from pathlib import Path

from .module_inspection import ModuleInspection
from .package_inspection import clean_requirement, PackageInspection
from .display import format_final_disaplay
from .settings import Settings, gather_args, gather_config


def iter_source_files(starting_dir, excludes, file_pattern):
    exclude_patterns = [re.compile(exclude) for exclude in excludes]

    for path in Path(starting_dir).rglob(file_pattern):
        spath = str(path)
        for exclude in exclude_patterns:
            if exclude.match(spath) is not None:
                break
        else:
            yield path


def main():
    arguments = gather_args()
    if arguments.pyproject:
        pyproject = Path(arguments.pyproject)
        if not pyproject.is_file():
            raise RuntimeWarning(f'Supplied --pyproject cannot be found: {pyproject}')
    else:
        pyproject = Path(arguments.search_path).resolve() / 'pyproject.toml'
        while not pyproject.is_file():
            if pyproject.parent == pyproject.parent.parent:
                pyproject = ''
                break
            pyproject = pyproject.parent.parent / 'pyproject.toml'

    if pyproject:
        user_settings = gather_config(pyproject)
    else:
        warnings.warn(f'Could not find {pyproject} to collect requirements')
        user_settings = {}
    user_settings.update(arguments._get_kwargs())
    settings = Settings(**user_settings)

    all_files = iter_source_files(settings.search_path, settings.exclude, '*')
    python_files = iter_source_files(settings.search_path, settings.exclude, '*.py')

    packages = PackageInspection(clean_requirement(req) for req in settings.packages)
    if pyproject:
        packages.update_from_pyproject(pyproject)
    for pip_requirements in settings.requirements:
        packages.update_from_pip_requirements(pip_requirements)
    packages.inspect_executables(all_files)

    modules = ModuleInspection()
    modules.inspect_imports(python_files)

    print(format_final_disaplay(settings, modules, packages))


if __name__ == '__main__':
    main()
