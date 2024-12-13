from reaktion_next.extension import ReaktionExtension
from rekuest_next.agents.registry import get_default_extension_registry


get_default_extension_registry().register(ReaktionExtension())
