import sys

from rich import print

from rich.columns import Columns
from rich.table import Table


def display_closing(settings, evaluation):
    if not settings.quiet and evaluation.passes():
        print('All Good!', file=sys.stderr)


def display_report(settings, evaluation):
    format_lookup = {
        'none': (lambda _: None),
        'line': format_line_output,
        'table': format_table_output,
        'extended-table': format_extended_table_output,
    }
    print(format_lookup[settings.report](evaluation))


def format_extended_table_output(evaluation):
    report = Table()
    report.add_column('Package')
    report.add_column('Used')
    report.add_column('Module')
    report.add_column('Used')
    for package in evaluation.packages.values():
        mods = list(package.modules)
        mods.sort()
        if not mods:
            report.add_row(package.package_name, 'True', '---', '---')
        else:
            mod = mods.pop()
            report.add_row(
                package.package_name,
                str(evaluation.evaluate_package(package.name)),
                mod,
                str(evaluation.evaluate_module(mod)),
            )
        for mod in package.modules:
            report.add_row(
                '---',
                '---',
                mod,
                str(evaluation.evaluate_module(mod)),
            )
    for mod in evaluation.modules:
        report.add_row('???', '???', mod, str(evaluation.evaluate_module(mod)))
    return report


def format_line_output(evaluation):
    report = ''
    excess_packages = evaluation.package_report()
    if excess_packages:
        report += f"Packages: {', '.join(excess_packages)}\n"
    excess_modules = evaluation.module_report()
    if excess_modules:
        report += f"Modules: {', '.join(excess_modules)}"
    return report


def format_table_output(evaluation):
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
