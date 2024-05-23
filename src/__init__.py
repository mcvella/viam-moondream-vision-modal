"""
This file registers the model with the Python SDK.
"""

from viam.services.vision import Vision
from viam.resource.registry import Registry, ResourceCreatorRegistration

from .moondream import moondream

Registry.register_resource_creator(Vision.SUBTYPE, moondream.MODEL, ResourceCreatorRegistration(moondream.new, moondream.validate))
