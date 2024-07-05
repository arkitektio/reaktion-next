from reaktion_next.extension import ReaktionExtension


def init_extensions(structure_reg):
    return ReaktionExtension(structure_registry=structure_reg)
