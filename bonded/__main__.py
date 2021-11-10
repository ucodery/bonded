import warnings
from pathlib import Path

from .bonded import inspect_imports, iter_source_files
from .display import format_final_disaplay
from .requirements import from_pip_requirements, from_pyproject, from_string
from .settings import Settings, gather_args, gather_config


def main():
    arguments = gather_args()
    if arguments.pyproject:
        pyproject = Path(arguments.pyproject)
        if not pyproject.is_file():
            raise RuntimeWarning(f"Supplied --pyproject cannot be found: {pyproject}")
    else:
        pyproject = Path(arguments.search_path).resolve() / "pyproject.toml"
        while not pyproject.is_file():
            if pyproject.parent == pyproject.parent.parent:
                pyproject = ""
                break
            pyproject = pyproject.parent.parent / "pyproject.toml"

    if pyproject:
        user_settings = gather_config(pyproject)
    else:
        warnings.warn(f"Could not find {pyproject} to collect requirements")
        user_settings = {}
    user_settings.update(arguments._get_kwargs())
    settings = Settings(**user_settings)

    given_requirements = from_string(settings.packages)
    given_requirements.extend(from_pip_requirements(settings.requirements))
    if pyproject:
        given_requirements.extend(from_pyproject(pyproject))

    all_files = iter_source_files(settings.search_path, settings.exclude)
    inspection = inspect_imports(all_files, given_requirements)
    print(format_final_disaplay(settings, inspection))


if __name__ == "__main__":
    main()
