from tabulate import tabulate

def format_final_disaplay(settings, inspection):
    success_message = "All Good!"
    if settings.verbose:
        return format_verbose_output(inspection) or success_message
    elif settings.quiet:
        return format_quiet_output(inspection)
    else:
        return format_normal_output(inspection) or success_message


def format_verbose_output(inspection):
    headers = ["Package", "Used", "Module", "Used"]
    columns = []
    for package in inspection.packages:
        if not package.modules:
            columns.append([package.package_name, True, "---", "---"])
        else:
            mod = package.modules.pop(0)
            columns.append([package.package_name, mod.found_import_stmt, mod.module_name, mod.found_import_stmt])
        for mod in package.modules:
            columns.append(["---", "---", mod.module_name, mod.found_import_stmt])
    return tabulate(columns, headers, tablefmt="fancy_grid")


def format_quiet_output(inspection):
    not_found = []
    for pkg in inspection.packages:
        if not any(mod.found_import_stmt for mod in pkg.modules):
            not_found.append(pkg.normalized_name)

    return ", ".join(not_found)


def format_normal_output(inspection):
    not_found = []
    for pkg in inspection.packages:
        if not any(mod.found_import_stmt for mod in pkg.modules):
            not_found.append(pkg)
    if not_found:
        headers = ["Unused Package", "Imports Not Found"]
        columns = [[p.package_name, ", ".join(m.module_name for m in p.modules)] for p in not_found]
        return tabulate(columns, headers, tablefmt="fancy_grid")
    return ""
