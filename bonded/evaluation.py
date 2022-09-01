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


class Evaluation:
    def __init__(
        self,
        packages,
        modules,
        ignore_packages=None,
        ignore_modules=None,
        project_modules=None,
        stdlib_modules=None,
    ):
        ignore_packages = ignore_packages or []
        ignore_modules = ignore_modules or []
        project_modules = project_modules or []
        stdlib_modules = stdlib_modules or stdlib_module_names
        self.package_scores = {
            pkg_name: PackageScore(
                package=pkg,
                user_ignored=pkg_name in ignore_packages,
            )
            for pkg_name, pkg in packages.items()
        }
        self.module_scores = {
            mod_name: ModuleScore(
                module=mod,
                stdlib=mod_name in stdlib_modules,
                local_project=mod_name in project_modules,
                user_ignored=mod_name in ignore_modules,
            )
            for mod_name, mod in modules.items()
        }

    def evaluate_with_packages(self):
        for mscore in self.module_scores.values():
            for pscore in self.package_scores.values():
                if mscore.module.name in pscore.package.modules:
                    mscore.belongs_to_package = pscore.package.name
                    break
                if mscore.module.name == pscore.package.name:
                    mscore.matches_package = pscore.package.name
                    break

    def evaluate_with_modules(self):
        for pscore in self.package_scores.values():
            for mod in pscore.package.modules:
                if mod in self.module_scores and self.module_scores[mod].passes():
                    pscore.module_imported = True
                    break

    def evaluate_with_extensions(self):
        passing = sum(score.passes() for score in self.package_scores.values()) + 1
        while passing > sum(score.passes() for score in self.package_scores.values()):
            for pscore in self.package_scores.values():
                if pscore.extension_used:
                    continue
                for ext in pscore.package.extends:
                    if (
                        ext in self.module_scores
                        and self.module_scores[ext].passes()
                        or ext in self.package_scores
                    ):
                        pscore.extension_used = True
                        break
            passing = sum(score.passes() for score in self.package_scores.values())

    def evaluate_with_executables(self, executables):
        for pscore in self.package_scores.values():
            for exe in pscore.package.executables:
                if exe in executables and executables[exe].found_executions:
                    pscore.executable_called = True
                    break

    def evaluate_build_backend(self, pyproject):
        with open(pyproject, 'rb') as pyproject_file:
            pyproject = tomli.load(pyproject_file)
            build_backend = pyproject.get('build-system', {}).get('build-backend')
            backend_path = pyproject.get('build-system', {}).get('backend-path')

            if not build_backend:
                return

            backend = Module(build_backend.split(':')[0].split('.')[0])
            if backend_path and backend.name in self.module_scores:
                self.module_scores[backend.name].local_project = True
            for pscore in self.package_scores.values():
                if backend.name in pscore.package.modules:
                    pscore.module_imported = True
                    break

    def apply_passes(self):
        """A series of workarounds for odd corners of the packaging world

        ANY of these that can be removed from here and worked into more general logic should be
        """
        for pscore in self.package_scores.values():
            if pscore.package.name == 'wheel':
                # wheel only extends distutils, but setuptools is more frequently imported
                # TODO check that setuptools is executed, not imported
                if 'setuptools' in self.module_scores and (
                    self.module_scores['setuptools'].passes()
                ):
                    pscore.extension_used = True
            elif (
                'pytest11' in pscore.package.extends
                and 'pytest' in self.package_scores
                and self.package_scores['pytest'].passes()
            ):
                pscore.extension_used = True

    def package_report(self):
        return {pscore.package for pscore in self.package_scores.values() if not pscore.passes()}

    def module_report(self):
        return {mscore.module for mscore in self.module_scores.values() if not mscore.passes()}


def evaluate_bonds(settings, modules, packages, executables):
    evaluation = Evaluation(
        packages,
        modules,
        ignore_packages=settings.ignore_packages,
        ignore_modules=settings.ignore_modules,
        project_modules=settings.project_modules,
    )
    evaluation.evaluate_with_packages()
    evaluation.evaluate_with_modules()
    evaluation.evaluate_with_executables(executables)
    evaluation.evaluate_with_extensions()
    if settings.pyproject:
        evaluation.evaluate_build_backend(settings.pyproject)
    evaluation.apply_passes()

    return Report(
        modules, packages, executables, evaluation.module_report(), evaluation.package_report()
    )
