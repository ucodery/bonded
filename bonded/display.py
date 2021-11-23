from tabulate import tabulate

def format_final_disaplay(settings, modules, packages):
    success_message = "All Good!"

    excess_packages = []
    for pkg in packages.values():
        if not any((modules[mod].found_import_stmt or modules[mod].found_import_fun) for mod in pkg.modules):
            excess_packages.append(pkg)

    excess_modules = []
    for mod in modules.iter_3rd_party(skip_modules=settings.project_modules):
        for pkg in packages.values():
            if modules[mod].module_name in pkg.modules:
                break
        else:
            excess_modules.append(modules[mod])

    if settings.verbose:
        return format_verbose_output(modules, excess_modules, packages) or success_message
    elif settings.quiet:
        return format_quiet_output(excess_modules, excess_packages)
    else:
        return format_normal_output(excess_modules, excess_packages) or success_message


def format_verbose_output(modules, excess_modules, packages):
    headers = ["Package", "Used", "Module", "Used"]
    columns = []
    for package in packages.values():
        mods = list(package.modules)
        mods.sort()
        if not mods:
            columns.append([package.package_name, True, "---", "---"])
        else:
            mod = mods.pop()
            columns.append(
                [
                    package.package_name,
                    any(modules[mod].found_import_stmt for mod in package.modules),
                    mod,
                    modules[mod].found_import_stmt
                ]
            )
        for mod in package.modules:
            columns.append(
                [
                    "---",
                    "---",
                    mod,
                    modules[mod].found_import_stmt
                ]
            )
    for mod in excess_modules:
        columns.append(["???", "???", mod.module_name, (mod.found_import_stmt or mod.found_import_fun)])
    return tabulate(columns, headers, tablefmt="fancy_grid")


def format_quiet_output(excess_modules, excess_packages):
    return (
        f"Packages: {', '.join(p.package_name for p in excess_packages)}\n"
        f"Modules: {', '.join(m.module_name for m in excess_modules)}"
    )


def format_normal_output(excess_modules, excess_packages):
    output = ""

    if excess_packages:
        headers = ["Unused Package", "Imports Not Found"]
        columns = [[p.package_name, ", ".join(m for m in p.modules)] for p in excess_packages]
        output += tabulate(columns, headers, tablefmt="fancy_grid")

    if excess_modules:
        headers = ["Modules Used Without a Package"]
        output += "\n"
        output += tabulate([[m.module_name] for m in excess_modules], headers, tablefmt="fancy_grid")

    return output
