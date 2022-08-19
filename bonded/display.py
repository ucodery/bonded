import sys

from rich import print

from rich.columns import Columns
from rich.table import Table


def display_closing(settings, report):
    if not settings.quiet and report.passes():
        print('All Good!', file=sys.stderr)


def display_report(settings, report):
    format_lookup = {
        'none': (lambda _: None),
        'line': format_line_output,
        'table': format_table_output,
        'extended-table': format_extended_table_output,
    }
    print(format_lookup[settings.report](report))


def format_extended_table_output(report):
    report = Table()
    report.add_column('Package')
    report.add_column('Used')
    report.add_column('Module')
    report.add_column('Used')
    for package in report.packages.values():
        mods = list(package.modules)
        mods.sort()
        if not mods:
            report.add_row(package.package_name, 'True', '---', '---')
        else:
            mod = mods.pop()
            report.add_row(
                package.package_name,
                str(any(report.modules[mod].found_import_stmt for mod in package.modules)),
                mod,
                str(report.modules[mod].found_import_stmt or report.modules[mod].found_import_fun),
            )
        for mod in package.modules:
            report.add_row(
                '---',
                '---',
                mod,
                str(report.modules[mod].found_import_stmt or report.modules[mod].found_import_fun),
            )
    for mod in report.excess_modules:
        report.add_row('???', '???', mod.name, str(mod.found_import_stmt or mod.found_import_fun))
    return report


def format_line_output(report):
    output = ''
    if report.excess_packages:
        output += f"Packages: {', '.join(p.package_name for p in report.excess_packages)}\n"
    if report.excess_modules:
        f"""Modules: {', '.join(m.name for m in report.excess_modules)}"""
    return output


def format_table_output(report):
    output = Columns()

    if report.excess_packages:
        excess_packages_report = Table()
        excess_packages_report.add_column('Unused Package')
        excess_packages_report.add_column('Imports Not Found')
        for ep in report.excess_packages:
            excess_packages_report.add_row(ep.package_name, ', '.join(m for m in ep.modules))
        output.add_renderable(excess_packages_report)

    if report.excess_modules:
        excess_modules_report = Table()
        excess_modules_report.add_column('Modules Used Without a Package')
        for em in report.excess_modules:
            excess_modules_report.add_row(em.name)
        output.add_renderable(excess_modules_report)

    return output
