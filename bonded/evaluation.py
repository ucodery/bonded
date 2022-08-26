import dataclasses
from typing import Optional

import tomli

from ._sys import stdlib_module_names

from .executable_inspection import ExecutableInspection

from .module_inspection import Module, ModuleInspection
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


@dataclasses.dataclass
class ModuleScore:
    belongs_to_package: Optional[str] = None
    matches_package: Optional[str] = None
    imported_with_statement: bool = False
    imported_with_function: bool = False
    stdlib: bool = False
    local_project: bool = False
    user_ignored: bool = False

    def passes(self):
        return (
            (self.belongs_to_package is not None or self.matches_package is not None)
            and (self.imported_with_statement or self.imported_with_function)
        ) or (self.stdlib or self.local_project or self.user_ignored)


class ModuleEvaluation:
    def __init__(self, modules, ignore_modules=None, project_modules=None, stdlib_modules=None):
        ignore_modules = ignore_modules or []
        project_modules = project_modules or []
        stdlib_modules = stdlib_modules or stdlib_module_names
        self.modules = modules
        self.module_scores = {
            mod_name: ModuleScore(
                imported_with_statement=mod.found_import_stmt,
                imported_with_function=mod.found_import_fun,
                stdlib=mod_name in stdlib_modules,
                local_project=mod_name in project_modules,
                user_ignored=mod_name in ignore_modules,
            )
            for mod_name, mod in self.modules.items()
        }

    def evaluate_with_packages(self, packages):
        for mod in self.modules.values():
            for pkg in packages.values():
                if mod.name in pkg.modules:
                    self.module_scores[mod.name].belongs_to_package = pkg.name
                    break
                if mod.name == pkg.name:
                    self.module_scores[mod.name].matches_package = pkg.name
                    break

    def report(self):
        return {
            self.modules[mod] for mod, score in self.module_scores.items() if not score.passes()
        }


# NOTE: just keep using Package?
@dataclasses.dataclass
class PackageScore:
    installed: bool = False
    platform_ignored: bool = False
    user_ignored: bool = False
    module_imported: bool = False
    extension_used: bool = False
    executable_called: bool = False

    def passes(self):
        return (
            self.installed
            and (self.module_imported or self.extension_used or self.executable_called)
        ) or (self.platform_ignored or self.user_ignored)


class PackgeEvaluation:
    def __init__(self, packages, ignore_packages=None):
        ignore_packages = ignore_packages or []
        self.packages = packages
        self.package_scores = {
            pkg_name: PackageScore(
                installed=pkg.installed,
                platform_ignored=(pkg.markers and not any(mark.evaluate() for mark in pkg.markers)),
                user_ignored=pkg_name in ignore_packages,
            )
            for pkg_name, pkg in self.packages.items()
        }

    def evaluate_with_modules(self, modules):
        for pkg in self.packages.values():
            for mod in pkg.modules:
                # TODO: should be based on ModuleEvaluation
                if mod in modules and (
                    modules[mod].found_import_stmt or modules[mod].found_import_fun
                ):
                    self.package_scores[pkg.name].module_imported = True
                    break

    def evaluate_with_extensions(self, modules, packages):
        passing = sum(score.passes() for score in self.package_scores.values()) + 1
        while passing > sum(score.passes() for score in self.package_scores.values()):
            for pkg in self.packages.values():
                if self.package_scores[pkg.name].extension_used:
                    continue
                for ext in pkg.extends:
                    # TODO: should be based on ModuleEvaluation
                    if (
                        ext in modules
                        and (modules[ext].found_import_stmt or modules[ext].found_import_fun)
                        or (ext in packages)
                    ):
                        self.package_scores[pkg.name].extension_used = True
                        break
            passing = sum(score.passes() for score in self.package_scores.values())

    def evaluate_with_executables(self, executables):
        for pkg in self.packages.values():
            for exe in pkg.executables:
                if exe in executables and executables[exe].found_executions:
                    self.package_scores[pkg.name].executable_called = True
                    break

    def evaluate_build_backend(self, pyproject):
        with open(pyproject, 'rb') as pyproject_file:
            pyproject = tomli.load(pyproject_file)
            build_backend = pyproject.get('build-system', {}).get('build-backend')
            # backend_path = pyproject.get('build-system', {}).get('backend-path')

            if not build_backend:
                return

            backend = Module(build_backend.split(':')[0].split('.')[0])
            for pkg in self.packages.values():
                if backend.name in pkg.modules:
                    self.package_scores[pkg.name].module_imported = True
                    # if backend_path: ModuleEvaluation.local_project = True
                    break

    def apply_passes(self, modules):
        """A series of workarounds for odd corners of the packaging world

        ANY of these that can be removed from here and worked into more general logic should be
        """
        for pkg in self.packages.values():
            if pkg.name == 'wheel':
                # wheel only extends distutils, but setuptools is more frequently imported
                # TODO check that setuptools is executed, not imported
                if 'setuptools' in modules and (
                    modules['setuptools'].found_import_stmt
                    or modules['setuptools'].found_import_fun
                ):
                    self.package_scores[pkg.name].extension_used = True
            elif (
                'pytest11' in pkg.extends
                and 'pytest' in self.package_scores
                and self.package_scores['pytest'].passes()
            ):
                self.package_scores[pkg.name].extension_used = True

    def report(self):
        return {
            self.packages[pkg] for pkg, score in self.package_scores.items() if not score.passes()
        }


def evaluate_bonds(settings, modules, packages, executables):
    module_evaluation = ModuleEvaluation(
        modules, ignore_modules=settings.ignore_modules, project_modules=settings.project_modules
    )
    module_evaluation.evaluate_with_packages(packages)

    excess_packages = PackgeEvaluation(packages, settings.ignore_packages)
    excess_packages.evaluate_with_modules(modules)
    excess_packages.evaluate_with_executables(executables)
    excess_packages.evaluate_with_extensions(modules, packages)
    if settings.pyproject:
        excess_packages.evaluate_build_backend(settings.pyproject)
    excess_packages.apply_passes(modules)

    return Report(
        modules, packages, executables, module_evaluation.report(), excess_packages.report()
    )
