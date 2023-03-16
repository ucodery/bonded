import sys

from rich import print

from rich.columns import Columns
from rich.table import Table

from ._sys import stdlib_module_names
from .evaluation import Confidence


def display_closing(settings, evaluation):
    if not settings.quiet and evaluation.passes():
        print('All Good!', file=sys.stderr)


def display_report(settings, evaluation):
    format_lookup = {
        'none': (lambda _, __: None),
        'line': format_line_output,
        'table': format_table_output,
        'extended-table': format_extended_table_output,
    }
    print(format_lookup[settings.report](settings, evaluation))


def format_line_output(settings, evaluation):
    report = ''
    excess_packages = evaluation.package_report()
    if excess_packages:
        report += f"Packages: {', '.join(excess_packages)}\n"
    excess_modules = evaluation.module_report()
    if excess_modules:
        report += f"Modules: {', '.join(excess_modules)}"
    return report


def format_table_output(settings, evaluation):
    report = Columns()

    excess_packages = evaluation.package_report()
    if excess_packages:
        excess_packages_report = Table()
        excess_packages_report.add_column('Unused Package')
        excess_packages_report.add_column('Imports Not Found')
        for ep in excess_packages:
            excess_packages_report.add_row(ep.package_name, ', '.join(m for m in ep.modules))
        report.add_renderable(excess_packages_report)

    excess_modules = evaluation.module_report()
    if excess_modules:
        excess_modules_report = Table()
        excess_modules_report.add_column('Modules Used Without a Package')
        for em in excess_modules:
            excess_modules_report.add_row(em.name)
        report.add_renderable(excess_modules_report)

    return report


def format_extended_table_output(settings, evaluation):
    report = Table()
    report.add_column('Package')
    report.add_column('Used')
    report.add_column('Module')
    report.add_column('Used')
    all_modules = set(evaluation.modules)

    for package in evaluation.packages.values():
        mods = list(package.modules)
        if not mods:
            report.add_row(
                package.package_name, str(evaluation.evaluate_package(package.name)), '---', '---'
            )
        else:
            mods.sort()
            mod = mods.pop(0)
            all_modules.discard(mod)
            report.add_row(
                package.package_name,
                str(evaluation.evaluate_package(package.name)),
                mod,
                str(evaluation.evaluate_module(mod)),
            )
        for mod in mods:
            all_modules.discard(mod)
            report.add_row(
                '---',
                '---',
                mod,
                str(evaluation.evaluate_module(mod)),
            )

    this_project_modules = [mod for mod in all_modules if mod in settings.project_modules]
    if this_project_modules:
        this_project_modules.sort()
        mod = this_project_modules.pop(0)
        all_modules.discard(mod)
        report.add_row(
            settings.search_path, str(Confidence.SKIPPED), mod, str(evaluation.evaluate_module(mod))
        )
        for mod in this_project_modules:
            all_modules.discard(mod)
            report.add_row('---', '---', mod, str(evaluation.evaluate_module(mod)))

    stdlib_modules = [mod for mod in all_modules if mod in stdlib_module_names]
    if stdlib_modules:
        stdlib_modules.sort()
        mod = stdlib_modules.pop(0)
        all_modules.discard(mod)
        report.add_row('python', str(Confidence.SKIPPED), mod, str(evaluation.evaluate_module(mod)))
        for mod in stdlib_modules:
            all_modules.discard(mod)
            report.add_row('---', '---', mod, str(evaluation.evaluate_module(mod)))

    for mod in all_modules:
        report.add_row('???', '???', mod, str(evaluation.evaluate_module(mod)))
    return report
