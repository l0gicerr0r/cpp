"""
Price Calculator Module - Custom OOP library for vehicle pricing and depreciation
"""

from datetime import datetime
from typing import Dict, Optional
from enum import Enum


class VehicleCondition(Enum):
    """Vehicle condition grades"""
    EXCELLENT = 1.0
    GOOD = 0.85
    FAIR = 0.70
    POOR = 0.50


class DepreciationModel:
    """Models vehicle depreciation over time"""
    
    # Annual depreciation rates by vehicle age
    DEPRECIATION_RATES = {
        1: 0.20,   # 20% first year
        2: 0.15,   # 15% second year
        3: 0.12,   # 12% third year
        4: 0.10,   # 10% fourth year
        5: 0.08,   # 8% fifth year and beyond
    }
    
    def __init__(self, original_price: float, year: int):
        self.original_price = original_price
        self.year = year
        self.age = datetime.now().year - year
    
    def calculate_current_value(self) -> float:
        """Calculate current market value based on depreciation"""
        value = self.original_price
        for year in range(1, self.age + 1):
            rate = self.DEPRECIATION_RATES.get(year, 0.08)
            value *= (1 - rate)
        return round(max(value, self.original_price * 0.10), 2)  # Min 10% of original
    
    def get_depreciation_schedule(self) -> Dict[int, float]:
        """Get year-by-year depreciation schedule"""
        schedule = {0: self.original_price}
        value = self.original_price
        for year in range(1, min(self.age + 6, 16)):  # Up to 15 years
            rate = self.DEPRECIATION_RATES.get(year, 0.08)
            value *= (1 - rate)
            schedule[year] = round(max(value, self.original_price * 0.10), 2)
        return schedule
    
    def get_total_depreciation(self) -> float:
        """Calculate total depreciation amount"""
        return round(self.original_price - self.calculate_current_value(), 2)
    
    def get_depreciation_percentage(self) -> float:
        """Calculate total depreciation as percentage"""
        return round((self.get_total_depreciation() / self.original_price) * 100, 1)


class PriceCalculator:
    """Calculator for vehicle pricing and valuations"""
    
    # Market adjustment factors
    MAKE_FACTORS = {
        'toyota': 1.10,
        'honda': 1.08,
        'ford': 1.00,
        'chevrolet': 0.98,
        'bmw': 1.15,
        'mercedes': 1.20,
        'audi': 1.12,
        'tesla': 1.25,
        'default': 1.00
    }
    
    def __init__(self):
        self.adjustments = []
    
    def calculate_market_value(self, make: str, model: str, year: int, 
                               base_price: float, condition: VehicleCondition = VehicleCondition.GOOD,
                               mileage: int = 50000) -> Dict:
        """Calculate estimated market value"""
        
        # Get depreciation
        depreciation_model = DepreciationModel(base_price, year)
        depreciated_value = depreciation_model.calculate_current_value()
        
        # Apply make factor
        make_factor = self.MAKE_FACTORS.get(make.lower(), self.MAKE_FACTORS['default'])
        
        # Apply condition factor
        condition_factor = condition.value
        
        # Apply mileage adjustment (assume 12000 miles/year average)
        expected_mileage = depreciation_model.age * 12000
        mileage_diff = expected_mileage - mileage
        mileage_factor = 1 + (mileage_diff / expected_mileage * 0.1) if expected_mileage > 0 else 1
        mileage_factor = max(0.7, min(1.3, mileage_factor))  # Cap between 70% and 130%
        
        # Calculate final value
        final_value = depreciated_value * make_factor * condition_factor * mileage_factor
        
        return {
            'vehicle': f"{year} {make} {model}",
            'base_price': base_price,
            'depreciated_value': depreciated_value,
            'make_adjustment': f"{(make_factor - 1) * 100:+.1f}%",
            'condition_adjustment': f"{(condition_factor - 1) * 100:+.1f}%",
            'mileage_adjustment': f"{(mileage_factor - 1) * 100:+.1f}%",
            'estimated_value': round(final_value, 2),
            'depreciation_total': depreciation_model.get_total_depreciation(),
            'depreciation_percent': depreciation_model.get_depreciation_percentage()
        }
    
    def compare_vehicles(self, vehicles: list) -> list:
        """Compare multiple vehicles and rank by value"""
        results = []
        for v in vehicles:
            value_data = self.calculate_market_value(
                v['make'], v['model'], v['year'], 
                v['price'], 
                VehicleCondition.GOOD
            )
            value_data['value_score'] = round(
                (value_data['estimated_value'] / v['price']) * 100, 1
            )
            results.append(value_data)
        
        return sorted(results, key=lambda x: x['value_score'], reverse=True)
    
    def get_price_suggestion(self, make: str, year: int, condition: str = 'good') -> Dict:
        """Get price suggestion for listing a vehicle"""
        condition_map = {
            'excellent': VehicleCondition.EXCELLENT,
            'good': VehicleCondition.GOOD,
            'fair': VehicleCondition.FAIR,
            'poor': VehicleCondition.POOR
        }
        
        # Base MSRP estimates by make
        base_msrp = {
            'toyota': 35000, 'honda': 32000, 'ford': 38000,
            'chevrolet': 36000, 'bmw': 55000, 'mercedes': 60000,
            'audi': 52000, 'tesla': 50000, 'default': 35000
        }
        
        msrp = base_msrp.get(make.lower(), base_msrp['default'])
        cond = condition_map.get(condition.lower(), VehicleCondition.GOOD)
        
        depreciation = DepreciationModel(msrp, year)
        base_value = depreciation.calculate_current_value()
        adjusted_value = base_value * cond.value
        
        return {
            'suggested_min': round(adjusted_value * 0.95, 2),
            'suggested_price': round(adjusted_value, 2),
            'suggested_max': round(adjusted_value * 1.05, 2),
            'condition': condition,
            'vehicle_age': depreciation.age
        }
