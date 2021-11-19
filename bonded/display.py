from tabulate import tabulate

def format_final_disaplay(settings, modules, packages):
    success_message = "All Good!"
    if settings.verbose:
        return format_verbose_output(modules, packages) or success_message
    elif settings.quiet:
        return format_quiet_output(modules, packages)
    else:
        return format_normal_output(modules, packages) or success_message


def format_verbose_output(modules, packages):
    headers = ["Package", "Used", "Module", "Used"]
    columns = []
    for package in packages.values():
        if not package.modules:
            columns.append([package.package_name, True, "---", "---"])
        else:
            mod = package.modules.pop()
            columns.append(
                [
                    package.package_name,
                    any(modules[mod].found_import_stmt for mod in package.modules),
                    modules[mod].module_name,
                    modules[mod].found_import_stmt
                ]
            )
        for mod in package.modules:
            columns.append(
                [
                    "---",
                    "---",
                    modules[mod].module_name,
                    modules[mod].found_import_stmt
                ]
            )
    return tabulate(columns, headers, tablefmt="fancy_grid")


def format_quiet_output(modules, packages):
    not_found = []
    for pkg in packages.values():
        if not any(modules[mod].found_import_stmt for mod in pkg.modules):
            not_found.append(pkg.normalized_name)

    return ", ".join(not_found)


def format_normal_output(modules, packages):
    not_found = []
    for pkg in packages.values():
        if not any(modules[mod].found_import_stmt for mod in pkg.modules):
            not_found.append(pkg)
    if not_found:
        headers = ["Unused Package", "Imports Not Found"]
        columns = [[p.package_name, ", ".join(m for m in p.modules)] for p in not_found]
        return tabulate(columns, headers, tablefmt="fancy_grid")
    return ""
