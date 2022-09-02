import tomli

from ._sys import stdlib_module_names


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
        for pkg_mod in package.modules:
            if self.evaluate_module(pkg_mod):
                return True
        return False

    def _package_extention_used(self, package):
        for extension in package.extends:
            if self.evaluate_package(extension) or self.evaluate_module(extension):
                return True
        return False

    def _package_executable_used(self, package):

        for executable in package.executables:
            if executable in self.executables and self.executables[executable].found_executions:
                return True
        return False

    def _package_used_anyway(self, package):
        """A series of workarounds for odd corners of the packaging world

        ANY of these that can be removed from here and worked into more general logic should be
        """
        # wheel only extends distutils, but setuptools is more frequently used
        if package.name == 'wheel' and self.evaluate_package('setuptools'):
            return True
        if 'pytest11' in package.extends and self.evaluate_package('pytest'):
            return True
        return False

    def evaluate_package(self, package):
        if package not in self.packages:
            return False
        pkg = self.packages[package]
        return (
            self._package_platform_ignored(pkg) or pkg.name in self.settings.ignore_packages
        ) or (
            pkg.installed
            and (
                self._package_module_used(pkg)
                or self._package_extention_used(pkg)
                or self._package_executable_used(pkg)
                or self._package_used_anyway(pkg)
            )
        )

    def _module_belongs_to_package(self, module):
        for pkg in self.packages.values():
            if module.name in pkg.modules:
                return True
            if module.name == pkg.name:
                return True
        return False

    def _module_used_for_build(self, module):
        if not self.settings.pyproject:
            return False
        with open(self.settings.pyproject, 'rb') as pyproject_file:
            pyproject = tomli.load(pyproject_file)
        build_backend = pyproject.get('build-system', {}).get('build-backend')
        backend = build_backend.split(':')[0].split('.')[0]
        return backend == module.name

    def evaluate_module(self, module):
        if module not in self.modules:
            return False
        mod = self.modules[module]
        return (
            mod.name in self.stdlib_modules
            or mod.name in self.settings.project_modules
            or mod.name in self.settings.ignore_modules
        ) or (
            self._module_belongs_to_package(mod)
            and (mod.found_import_stmt or mod.found_import_fun or self._module_used_for_build(mod))
        )

    def package_report(self):
        return {
            package for name, package in self.packages.items() if not self.evaluate_package(name)
        }

    def module_report(self):
        return {module for name, module in self.modules.items() if not self.evaluate_module(name)}

    def passes(self):
        return True


def evaluate_bonds(settings, modules, packages, executables):
    return Evaluation(
        packages,
        modules,
        executables,
        settings,
    )
