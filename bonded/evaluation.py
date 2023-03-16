from enum import IntEnum
from functools import cache

import tomli

from ._sys import stdlib_module_names


class Confidence(IntEnum):
    NONE = 0
    VERY_LOW = 5
    LOW = 10
    MEDIUM = 15
    HIGH = 20
    VERY_HIGH = 25
    SKIPPED = 30


class Evaluation:
    def __init__(
        self,
        packages,
        modules,
        executables,
        settings,
        stdlib_modules=None,
    ):
        self.packages = packages
        self.modules = modules
        self.executables = executables
        self.settings = settings
        self.stdlib_modules = stdlib_modules or stdlib_module_names

    def _package_platform_ignored(self, package):
        return package.markers and not any(mark.evaluate() for mark in package.markers)

    def _package_module_used(self, package):
        if not package.modules:
            return Confidence.NONE
        return max(self.evaluate_module(pkg_mod) for pkg_mod in package.modules)

    def _package_extention_used(self, package):
        extension_used = Confidence.NONE
        for extension in package.extends:
            if extension == package.name:
                continue
            extension_used = max(
                extension_used, self.evaluate_package(extension), self.evaluate_module(extension)
            )
        return extension_used

    def _package_executable_used(self, package):
        executable_used = Confidence.NONE
        for executable in package.executables:
            if executable in self.executables and self.executables[executable].found_executions:
                # TODO: check file type
                return Confidence.MEDIUM
        return executable_used

    def _package_used_anyway(self, package):
        """A series of workarounds for odd corners of the packaging world

        ANY of these that can be removed from here and worked into more general logic should be
        """
        # wheel only extends distutils, but setuptools is more frequently used
        if package.name == 'wheel' and self.evaluate_package('setuptools'):
            return Confidence.HIGH
        if 'pytest11' in package.extends and self.evaluate_package('pytest'):
            return Confidence.HIGH
        return Confidence.NONE

    @cache
    def evaluate_package(self, package):
        if package not in self.packages:
            return Confidence.NONE
        pkg = self.packages[package]
        if self._package_platform_ignored(pkg) or pkg.name in self.settings.ignore_packages:
            return Confidence.SKIPPED
        if not pkg.installed:
            return Confidence.NONE
        return max(
            self._package_module_used(pkg),
            self._package_extention_used(pkg),
            self._package_executable_used(pkg),
            self._package_used_anyway(pkg),
        )

    def _module_belongs_to_package(self, module):
        for pkg in self.packages.values():
            if module.name in pkg.modules:
                return True
            if module.name == pkg.name:
                return True
        return False

    def _module_imported(self, module):
        if module.found_import_stmt:
            return Confidence.VERY_HIGH
        if module.found_import_fun:
            return Confidence.HIGH
        return Confidence.NONE

    def _module_used_for_build(self, module):
        if not self.settings.pyproject:
            return Confidence.NONE
        with open(self.settings.pyproject, 'rb') as pyproject_file:
            pyproject = tomli.load(pyproject_file)
        build_backend = pyproject.get('build-system', {}).get('build-backend')
        backend = build_backend.split(':')[0].split('.')[0]
        if backend == module:
            return Confidence.HIGH
        return Confidence.NONE

    @cache
    def evaluate_module(self, module):
        if module not in self.modules:
            return self._module_used_for_build(module)
        mod = self.modules[module]
        if (
            mod.name in self.stdlib_modules
            or mod.name in self.settings.project_modules
            or mod.name in self.settings.ignore_modules
        ):
            return Confidence.SKIPPED
        if not self._module_belongs_to_package(mod):
            return Confidence.NONE
        return max(
            self._module_imported(mod),
            self._module_used_for_build(module),
        )

    def package_report(self):
        return {
            package for name, package in self.packages.items() if not self.evaluate_package(name)
        }

    def module_report(self):
        return {module for name, module in self.modules.items() if not self.evaluate_module(name)}

    def passes(self):
        return not bool(self.package_report() or self.module_report())


def evaluate_bonds(settings, modules, packages, executables):
    return Evaluation(
        packages,
        modules,
        executables,
        settings,
    )
