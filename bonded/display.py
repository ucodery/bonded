from tabulate import tabulate


def format_final_disaplay(settings, modules, packages, executables):
    success_message = '' if settings.quiet else 'All Good!'

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

    if settings.report == 'extended-table':
        return format_extended_table_output(modules, excess_modules, packages) or success_message
    elif settings.report == 'table':
        return format_table_output(excess_modules, excess_packages) or success_message
    elif settings.report == 'line':
        return format_line_output(excess_modules, excess_packages) or success_message
    elif settings.report == 'none':
        return success_message


def format_extended_table_output(modules, excess_modules, packages):
    headers = ['Package', 'Used', 'Module', 'Used']
    columns = []
    for package in packages.values():
        mods = list(package.modules)
        mods.sort()
        if not mods:
            columns.append([package.package_name, True, '---', '---'])
        else:
            mod = mods.pop()
            columns.append(
                [
                    package.package_name,
                    any(modules[mod].found_import_stmt for mod in package.modules),
                    mod,
                    modules[mod].found_import_stmt,
                ]
            )
        for mod in package.modules:
            columns.append(['---', '---', mod, modules[mod].found_import_stmt])
    for mod in excess_modules:
        columns.append(
            [
                '???',
                '???',
                mod.name,
                (mod.found_import_stmt or mod.found_import_fun),
            ]
        )
    return tabulate(columns, headers, tablefmt='fancy_grid')


def format_line_output(excess_modules, excess_packages):
    output = ''
    if excess_packages:
        output += f"Packages: {', '.join(p.package_name for p in excess_packages)}\n"
    if excess_modules:
        f"""Modules: {', '.join(m.name for m in excess_modules)}"""
    return output


def format_table_output(excess_modules, excess_packages):
    output = ''

    if excess_packages:
        headers = ['Unused Package', 'Imports Not Found']
        columns = [[p.package_name, ', '.join(m for m in p.modules)] for p in excess_packages]
        output += tabulate(columns, headers, tablefmt='fancy_grid')

    if excess_modules:
        headers = ['Modules Used Without a Package']
        output += '\n'
        output += tabulate(
            [[m.name] for m in excess_modules],
            headers,
            tablefmt='fancy_grid',
        )

    return output
