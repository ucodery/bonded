import dataclasses
from typing import Optional

import tomli

from ._sys import stdlib_module_names

from .executable_inspection import ExecutableInspection

from .module_inspection import Module, ModuleInspection
from .package_inspection import Package, PackageInspection


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
    module: Module
    belongs_to_package: Optional[str] = None
    matches_package: Optional[str] = None
    stdlib: bool = False
    local_project: bool = False
    user_ignored: bool = False

    def passes(self):
        return (
            (self.belongs_to_package is not None or self.matches_package is not None)
            and (self.module.found_import_stmt or self.module.found_import_fun)
        ) or (self.stdlib or self.local_project or self.user_ignored)


class ModuleEvaluation(dict):
    def __init__(self, modules, ignore_modules=None, project_modules=None, stdlib_modules=None):
        ignore_modules = ignore_modules or []
        project_modules = project_modules or []
        stdlib_modules = stdlib_modules or stdlib_module_names
        self.modules = modules
        self.module_scores = {
            mod_name: ModuleScore(
                mod,
                stdlib=mod_name in stdlib_modules,
                local_project=mod_name in project_modules,
                user_ignored=mod_name in ignore_modules,
            )
            for mod_name, mod in self.modules.items()
        }

    def evaluate_with_packages(self, packages):
        for mscore in self.values():
            for pkg in packages.values():
                if mscore.module.name in pkg.modules:
                    mscore.belongs_to_package = pkg.name
                    break
                if mscore.module.name == pkg.name:
                    mscore.matches_package = pkg.name
                    break

    def report(self):
        return {mscore.module for mscore in self.values() if not mscore.passes()}


@dataclasses.dataclass
class PackageScore:
    package: Package
    user_ignored: bool = False
    module_imported: bool = False
    extension_used: bool = False
    executable_called: bool = False

    @property
    def platform_ignored(self):
        return self.package.markers and not any(mark.evaluate() for mark in self.package.markers)

    def passes(self):
        return (
            self.package.installed
            and (self.module_imported or self.extension_used or self.executable_called)
        ) or (self.platform_ignored or self.user_ignored)


class PackgeEvaluation(dict):
    def __init__(self, packages, ignore_packages=None):
        ignore_packages = ignore_packages or []
        super().__init__(
            (
                pkg_name,
                PackageScore(
                    package=pkg,
                    user_ignored=pkg_name in ignore_packages,
                ),
            )
            for pkg_name, pkg in packages.items()
        )

    def evaluate_with_modules(self, modules):
        for pscore in self.values():
            for mod in pscore.package.modules:
                # TODO: should be based on ModuleEvaluation
                if mod in modules and (
                    modules[mod].found_import_stmt or modules[mod].found_import_fun
                ):
                    self[pscore.package.name].module_imported = True
                    break

    def evaluate_with_extensions(self, modules):
        passing = sum(score.passes() for score in self.values()) + 1
        while passing > sum(score.passes() for score in self.values()):
            for pscore in self.values():
                if self[pscore.package.name].extension_used:
                    continue
                for ext in pscore.package.extends:
                    # TODO: should be based on ModuleEvaluation
                    if (
                        ext in modules
                        and (modules[ext].found_import_stmt or modules[ext].found_import_fun)
                        or (ext in self)
                    ):
                        self[pscore.package.name].extension_used = True
                        break
            passing = sum(score.passes() for score in self.values())

    def evaluate_with_executables(self, executables):
        for pscore in self.values():
            for exe in pscore.package.executables:
                if exe in executables and executables[exe].found_executions:
                    self[pscore.package.name].executable_called = True
                    break

    def evaluate_build_backend(self, pyproject):
        with open(pyproject, 'rb') as pyproject_file:
            pyproject = tomli.load(pyproject_file)
            build_backend = pyproject.get('build-system', {}).get('build-backend')
            # backend_path = pyproject.get('build-system', {}).get('backend-path')

            if not build_backend:
                return

            backend = Module(build_backend.split(':')[0].split('.')[0])
            for pscore in self.values():
                if backend.name in pscore.package.modules:
                    self[pscore.package.name].module_imported = True
                    # if backend_path: ModuleEvaluation.local_project = True
                    break

    def apply_passes(self, modules):
        """A series of workarounds for odd corners of the packaging world

        ANY of these that can be removed from here and worked into more general logic should be
        """
        for pscore in self.values():
            if pscore.package.name == 'wheel':
                # wheel only extends distutils, but setuptools is more frequently imported
                # TODO check that setuptools is executed, not imported
                if 'setuptools' in modules and (
                    modules['setuptools'].found_import_stmt
                    or modules['setuptools'].found_import_fun
                ):
                    self[pscore.package.name].extension_used = True
            elif (
                'pytest11' in pscore.package.extends
                and 'pytest' in self
                and self['pytest'].passes()
            ):
                self[pscore.package.name].extension_used = True

    def report(self):
        return {pscore.package for pscore in self.values() if not pscore.passes()}


def evaluate_bonds(settings, modules, packages, executables):
    module_evaluation = ModuleEvaluation(
        modules, ignore_modules=settings.ignore_modules, project_modules=settings.project_modules
    )
    module_evaluation.evaluate_with_packages(packages)

    excess_packages = PackgeEvaluation(packages, settings.ignore_packages)
    excess_packages.evaluate_with_modules(modules)
    excess_packages.evaluate_with_executables(executables)
    excess_packages.evaluate_with_extensions(modules)
    if settings.pyproject:
        excess_packages.evaluate_build_backend(settings.pyproject)
    excess_packages.apply_passes(modules)

    return Report(
        modules, packages, executables, module_evaluation.report(), excess_packages.report()
    )
