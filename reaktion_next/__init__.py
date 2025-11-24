try:
    from .rekuest import ReaktionExtension
except ImportError as e:
    raise e

from reaktion_next.extension import ReaktionExtension


__all__ = ["structure_reg", "ReaktionExtension"]
