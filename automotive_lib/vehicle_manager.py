"""
Vehicle Manager Module - Custom OOP library for vehicle data management
"""

from datetime import datetime
from typing import List, Dict, Optional
import json


class Vehicle:
    """Represents a vehicle with its attributes"""
    
    def __init__(self, make: str, model: str, year: int, price: float, description: str = ""):
        self.make = make
        self.model = model
        self.year = year
        self.price = price
        self.description = description
        self.created_at = datetime.utcnow()
    
    def to_dict(self) -> Dict:
        return {
            'make': self.make,
            'model': self.model,
            'year': self.year,
            'price': self.price,
            'description': self.description,
            'created_at': self.created_at.isoformat()
        }
    
    def get_age(self) -> int:
        """Calculate vehicle age in years"""
        return datetime.now().year - self.year
    
    def __repr__(self):
        return f"Vehicle({self.year} {self.make} {self.model})"


class VehicleManager:
    """Manages a collection of vehicles with CRUD operations"""
    
    def __init__(self):
        self._vehicles: List[Vehicle] = []
    
    def add_vehicle(self, vehicle: Vehicle) -> bool:
        """Add a vehicle to the collection"""
        if isinstance(vehicle, Vehicle):
            self._vehicles.append(vehicle)
            return True
        return False
    
    def remove_vehicle(self, index: int) -> Optional[Vehicle]:
        """Remove and return a vehicle by index"""
        if 0 <= index < len(self._vehicles):
            return self._vehicles.pop(index)
        return None
    
    def get_vehicle(self, index: int) -> Optional[Vehicle]:
        """Get a vehicle by index"""
        if 0 <= index < len(self._vehicles):
            return self._vehicles[index]
        return None
    
    def get_all_vehicles(self) -> List[Vehicle]:
        """Return all vehicles"""
        return self._vehicles.copy()
    
    def filter_by_make(self, make: str) -> List[Vehicle]:
        """Filter vehicles by make"""
        return [v for v in self._vehicles if v.make.lower() == make.lower()]
    
    def filter_by_year_range(self, min_year: int, max_year: int) -> List[Vehicle]:
        """Filter vehicles by year range"""
        return [v for v in self._vehicles if min_year <= v.year <= max_year]
    
    def filter_by_price_range(self, min_price: float, max_price: float) -> List[Vehicle]:
        """Filter vehicles by price range"""
        return [v for v in self._vehicles if min_price <= v.price <= max_price]
    
    def count(self) -> int:
        """Return total number of vehicles"""
        return len(self._vehicles)


class VehicleAnalytics:
    """Analytics engine for vehicle data analysis"""
    
    def __init__(self, vehicles: List[Dict] = None):
        self.vehicles = vehicles or []
    
    def set_vehicles(self, vehicles: List[Dict]):
        """Set the vehicle data for analysis"""
        self.vehicles = vehicles
    
    def get_average_price(self) -> float:
        """Calculate average price of all vehicles"""
        if not self.vehicles:
            return 0.0
        total = sum(v.get('price', 0) for v in self.vehicles)
        return round(total / len(self.vehicles), 2)
    
    def get_price_range(self) -> Dict:
        """Get min and max prices"""
        if not self.vehicles:
            return {'min': 0, 'max': 0}
        prices = [v.get('price', 0) for v in self.vehicles]
        return {'min': min(prices), 'max': max(prices)}
    
    def get_vehicles_by_year(self) -> Dict[int, int]:
        """Count vehicles by year"""
        year_count = {}
        for v in self.vehicles:
            year = v.get('year', 0)
            year_count[year] = year_count.get(year, 0) + 1
        return dict(sorted(year_count.items()))
    
    def get_vehicles_by_make(self) -> Dict[str, int]:
        """Count vehicles by make"""
        make_count = {}
        for v in self.vehicles:
            make = v.get('make', 'Unknown')
            make_count[make] = make_count.get(make, 0) + 1
        return dict(sorted(make_count.items()))
    
    def get_average_age(self) -> float:
        """Calculate average age of vehicles"""
        if not self.vehicles:
            return 0.0
        current_year = datetime.now().year
        total_age = sum(current_year - v.get('year', current_year) for v in self.vehicles)
        return round(total_age / len(self.vehicles), 1)
    
    def get_summary(self) -> Dict:
        """Get a complete analytics summary"""
        return {
            'total_vehicles': len(self.vehicles),
            'average_price': self.get_average_price(),
            'price_range': self.get_price_range(),
            'average_age': self.get_average_age(),
            'by_make': self.get_vehicles_by_make(),
            'by_year': self.get_vehicles_by_year()
        }
    
    def to_json(self) -> str:
        """Export analytics summary as JSON"""
        return json.dumps(self.get_summary(), indent=2)
