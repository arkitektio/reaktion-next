from reaktion_next.extension import ReaktionExtension


def init_extensions(structure_reg):
    print("Imported Reaktion next extensions")
    return ReaktionExtension(structure_registry=structure_reg)
