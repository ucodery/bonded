import dataclasses

from .executable_inspection import ExecutableInspection

from .module_inspection import ModuleInspection
from .package_inspection import PackageInspection


@dataclasses.dataclass
class Report:
    modules: ModuleInspection
    packages: PackageInspection
    execuatables: ExecutableInspection
    excess_modules: set
    excess_packages: set

    def passes(self):
        return True


def evaluate_bonds(settings, modules, packages, executables):
    excess_modules = set()
    for mod in modules.iter_3rd_party(
        skip_modules=(settings.ignore_modules + settings.project_modules)
    ):
        for pkg in packages.values():
            if modules[mod].name in pkg.modules:
                break
            if modules[mod].name == pkg.name:
                break
        else:
            excess_modules.add(modules[mod])

    excess_packages = set()
    for pkg in packages.values():
        if not any(
            (modules[mod].found_import_stmt or modules[mod].found_import_fun) for mod in pkg.modules
        ):
            if not any(
                (modules[mod].found_import_stmt or modules[mod].found_import_fun)
                for mod in pkg.extends
            ):
                if not any(executables[e].found_executions for e in pkg.executables):
                    excess_packages.add(pkg)

    # this needs to be repeated until no more packages are removed
    for pkg in set(excess_packages):
        if any(ext in (packages.keys() ^ excess_packages) for ext in pkg.extends):
            excess_packages.remove(pkg)
        elif pkg.markers and not any(mark.evaluate() for mark in pkg.markers):
            excess_packages.remove(pkg)

    # Workarounds for problem packages
    for pkg in set(excess_packages):
        if pkg.package_name == 'wheel':
            # wheel only extends distutils, but setuptools is more frequently imported
            if modules['setuptools'].found_import_stmt or modules['setuptools'].found_import_fun:
                excess_packages.remove(pkg)
        elif 'pytest11' in pkg.extends and 'pytest' in (packages.keys() ^ excess_packages):
            excess_packages.remove(pkg)

    return Report(modules, packages, executables, excess_modules, excess_packages)
