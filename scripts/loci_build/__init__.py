"""Helpers for building palace furniture and props from code.

A palace script typically resets a collection, then fills it with Batch
objects (many primitives merged into one mesh) and a few lights.
"""
from .batch import Batch
from .materials import emissive, fabric, plain
from .scene import point_light, reset_collection

__all__ = ["Batch", "emissive", "fabric", "plain", "point_light", "reset_collection"]
