"""
Automotive Library - A custom OOP library for vehicle management and analytics
"""

from .vehicle_manager import VehicleManager, VehicleAnalytics
from .price_calculator import PriceCalculator, DepreciationModel

__version__ = "1.0.0"
__all__ = ['VehicleManager', 'VehicleAnalytics', 'PriceCalculator', 'DepreciationModel']
