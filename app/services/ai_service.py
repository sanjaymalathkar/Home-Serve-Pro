"""
AI/ML Service for HomeServe Pro.
Handles pincode clustering, travel time prediction, and vendor allocation.
"""

import numpy as np
from datetime import datetime, timedelta
import os


class PincodePulseEngine:
    """
    AI-powered pincode clustering and demand prediction.
    Uses K-means clustering to group pincodes by demand.
    """
    
    def __init__(self):
        self.model = None
        self.model_path = os.path.join(
            os.getenv('AI_MODEL_PATH', './models'),
            os.getenv('PINCODE_CLUSTERING_MODEL', 'pincode_cluster.pkl')
        )
    
    def load_model(self):
        """Load pre-trained clustering model."""
        try:
            # In production, load actual model
            # import joblib
            # self.model = joblib.load(self.model_path)
            pass
        except Exception as e:
            print(f"Error loading pincode clustering model: {e}")
    
    def cluster_pincodes(self, pincodes_data):
        """
        Cluster pincodes based on demand patterns.
        
        Args:
            pincodes_data (list): List of dicts with pincode and booking count
            
        Returns:
            dict: Clustered pincodes with demand levels
        """
        try:
            # Simplified clustering logic (in production, use actual ML model)
            clusters = {
                'high_demand': [],
                'medium_demand': [],
                'low_demand': []
            }
            
            for data in pincodes_data:
                booking_count = data.get('booking_count', 0)
                pincode = data.get('pincode')
                
                if booking_count > 50:
                    clusters['high_demand'].append(pincode)
                elif booking_count > 20:
                    clusters['medium_demand'].append(pincode)
                else:
                    clusters['low_demand'].append(pincode)
            
            return clusters
            
        except Exception as e:
            print(f"Error clustering pincodes: {e}")
            return {'high_demand': [], 'medium_demand': [], 'low_demand': []}
    
    def predict_demand(self, pincode, date=None):
        """
        Predict demand for a pincode on a specific date.
        
        Args:
            pincode (str): Pincode to predict
            date (datetime): Date for prediction
            
        Returns:
            float: Predicted demand score (0-1)
        """
        try:
            # Simplified prediction (in production, use actual ML model)
            # Consider factors like day of week, season, historical data
            
            if date is None:
                date = datetime.utcnow()
            
            # Weekend boost
            weekend_factor = 1.2 if date.weekday() >= 5 else 1.0
            
            # Random baseline (replace with actual model prediction)
            base_demand = np.random.uniform(0.3, 0.8)
            
            return min(base_demand * weekend_factor, 1.0)
            
        except Exception as e:
            print(f"Error predicting demand: {e}")
            return 0.5


class SmartBufferingEngine:
    """
    AI-powered travel time prediction and job scheduling.
    Uses Google Maps API and ML to optimize vendor schedules.
    """
    
    def __init__(self):
        self.google_maps_key = os.getenv('GOOGLE_MAPS_API_KEY', '')
        self.model = None
    
    def predict_travel_time(self, origin, destination):
        """
        Predict travel time between two locations.
        
        Args:
            origin (str): Origin address or pincode
            destination (str): Destination address or pincode
            
        Returns:
            int: Predicted travel time in minutes
        """
        try:
            # In production, use Google Maps Distance Matrix API
            # import googlemaps
            # gmaps = googlemaps.Client(key=self.google_maps_key)
            # result = gmaps.distance_matrix(origin, destination)
            # duration = result['rows'][0]['elements'][0]['duration']['value'] / 60
            
            # Simplified prediction
            base_time = np.random.randint(15, 45)
            return base_time
            
        except Exception as e:
            print(f"Error predicting travel time: {e}")
            return 30  # Default 30 minutes
    
    def calculate_buffer_time(self, service_duration, travel_time):
        """
        Calculate optimal buffer time between jobs.
        
        Args:
            service_duration (int): Service duration in minutes
            travel_time (int): Travel time in minutes
            
        Returns:
            int: Buffer time in minutes
        """
        try:
            # Add 20% buffer for service + full travel time + 10 min prep
            service_buffer = int(service_duration * 0.2)
            total_buffer = service_buffer + travel_time + 10
            
            return total_buffer
            
        except Exception as e:
            print(f"Error calculating buffer: {e}")
            return 30
    
    def optimize_schedule(self, bookings, vendor_location):
        """
        Optimize vendor schedule using traveling salesman approach.
        
        Args:
            bookings (list): List of booking dicts with locations
            vendor_location (str): Vendor's current location
            
        Returns:
            list: Optimized booking order
        """
        try:
            # Simplified optimization (in production, use actual TSP algorithm)
            # For now, just sort by pincode proximity
            
            if not bookings:
                return []
            
            # Sort bookings by pincode (simplified proximity)
            sorted_bookings = sorted(bookings, key=lambda x: x.get('pincode', ''))
            
            return sorted_bookings
            
        except Exception as e:
            print(f"Error optimizing schedule: {e}")
            return bookings


class VendorAllocationEngine:
    """
    AI-powered vendor allocation and matching.
    Considers ratings, location, availability, and workload.
    """
    
    def __init__(self):
        pass
    
    def calculate_vendor_score(self, vendor, booking):
        """
        Calculate vendor suitability score for a booking.
        
        Args:
            vendor (dict): Vendor data
            booking (dict): Booking data
            
        Returns:
            float: Suitability score (0-1)
        """
        try:
            score = 0.0
            
            # Rating factor (40%)
            rating = vendor.get('ratings', 0)
            rating_score = rating / 5.0
            score += rating_score * 0.4
            
            # Availability factor (30%)
            if vendor.get('availability', False):
                score += 0.3
            
            # Location proximity (20%)
            vendor_pincodes = vendor.get('pincodes', [])
            booking_pincode = booking.get('pincode', '')
            if booking_pincode in vendor_pincodes:
                score += 0.2
            
            # Experience factor (10%)
            completed_jobs = vendor.get('completed_jobs', 0)
            experience_score = min(completed_jobs / 100, 1.0)
            score += experience_score * 0.1
            
            return score
            
        except Exception as e:
            print(f"Error calculating vendor score: {e}")
            return 0.0
    
    def allocate_vendor(self, vendors, booking):
        """
        Allocate best vendor for a booking.
        
        Args:
            vendors (list): List of available vendors
            booking (dict): Booking data
            
        Returns:
            dict: Best matched vendor or None
        """
        try:
            if not vendors:
                return None
            
            # Calculate scores for all vendors
            vendor_scores = []
            for vendor in vendors:
                score = self.calculate_vendor_score(vendor, booking)
                vendor_scores.append((vendor, score))
            
            # Sort by score descending
            vendor_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Return best vendor
            return vendor_scores[0][0] if vendor_scores else None
            
        except Exception as e:
            print(f"Error allocating vendor: {e}")
            return vendors[0] if vendors else None


class PricingOptimizationEngine:
    """
    Dynamic pricing based on demand, location, and time.
    """
    
    def __init__(self):
        self.pincode_engine = PincodePulseEngine()
    
    def calculate_dynamic_price(self, base_price, pincode, date=None):
        """
        Calculate dynamic price based on demand.
        
        Args:
            base_price (float): Base service price
            pincode (str): Service pincode
            date (datetime): Service date
            
        Returns:
            float: Adjusted price
        """
        try:
            # Get demand prediction
            demand = self.pincode_engine.predict_demand(pincode, date)
            
            # Apply demand multiplier (max 1.5x for high demand)
            demand_multiplier = 1.0 + (demand * 0.5)
            
            # Peak hours multiplier (8 AM - 6 PM)
            if date:
                hour = date.hour
                peak_multiplier = 1.1 if 8 <= hour <= 18 else 1.0
            else:
                peak_multiplier = 1.0
            
            # Calculate final price
            final_price = base_price * demand_multiplier * peak_multiplier
            
            return round(final_price, 2)
            
        except Exception as e:
            print(f"Error calculating dynamic price: {e}")
            return base_price


# Singleton instances
pincode_pulse = PincodePulseEngine()
smart_buffering = SmartBufferingEngine()
vendor_allocation = VendorAllocationEngine()
pricing_optimization = PricingOptimizationEngine()

