import geocoder
import folium
from folium import plugins
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from datetime import datetime
import requests
import polyline
import tkinter as tk
from tkinter import messagebox
import webbrowser

class LocationService:
    def __init__(self):
        self.geolocator = Nominatim(user_agent="pothole_detector")
        
    def get_current_location(self):
        """Get current location using interactive map"""
        try:
            # Create an HTML file with an interactive map
            html_content = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Select Location</title>
                <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css"/>
                <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
                <style>
                    #map { height: 500px; width: 100%; }
                    #coordinates { 
                        position: absolute; 
                        bottom: 20px; 
                        left: 50%; 
                        transform: translateX(-50%);
                        background: white;
                        padding: 10px;
                        border-radius: 5px;
                        z-index: 1000;
                    }
                    #copyButton {
                        margin-left: 10px;
                        padding: 5px 10px;
                        cursor: pointer;
                    }
                </style>
            </head>
            <body>
                <div id="map"></div>
                <div id="coordinates">
                    Click on the map to select your location
                    <button id="copyButton" onclick="copyCoords()" style="display: none;">Copy Coordinates</button>
                </div>
                <script>
                    // Initialize map
                    var map = L.map('map').setView([12.9716, 77.5946], 15); // Increased zoom level for better accuracy
                    
                    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                        attribution: '© OpenStreetMap contributors'
                    }).addTo(map);

                    // Add zoom controls
                    L.control.zoom({
                        position: 'bottomright',
                        zoomInTitle: 'Zoom in',
                        zoomOutTitle: 'Zoom out'
                    }).addTo(map);

                    var marker;
                    var currentCoords = '';
                    
                    function copyCoords() {
                        navigator.clipboard.writeText(currentCoords).then(function() {
                            alert('Coordinates copied to clipboard!');
                        }).catch(function() {
                            // Fallback for older browsers
                            var textArea = document.createElement("textarea");
                            textArea.value = currentCoords;
                            document.body.appendChild(textArea);
                            textArea.select();
                            document.execCommand('copy');
                            document.body.removeChild(textArea);
                            alert('Coordinates copied to clipboard!');
                        });
                    }
                    
                    // Try to get user's location
                    map.locate({setView: true, maxZoom: 16});
                    
                    map.on('locationfound', function(e) {
                        if (marker) map.removeLayer(marker);
                        marker = L.marker(e.latlng).addTo(map);
                        currentCoords = `${e.latlng.lat.toFixed(6)},${e.latlng.lng.toFixed(6)}`;
                        document.getElementById('coordinates').innerHTML = `Selected: ${currentCoords} <button id="copyButton" onclick="copyCoords()">Copy Coordinates</button>`;
                    });
                    
                    map.on('click', function(e) {
                        if (marker) map.removeLayer(marker);
                        marker = L.marker(e.latlng).addTo(map);
                        currentCoords = `${e.latlng.lat.toFixed(6)},${e.latlng.lng.toFixed(6)}`;
                        document.getElementById('coordinates').innerHTML = `Selected: ${currentCoords} <button id="copyButton" onclick="copyCoords()">Copy Coordinates</button>`;
                    });
                </script>
            </body>
            </html>
            """
            
            # Save and open the HTML file
            with open("select_location.html", "w", encoding='utf-8') as f:
                f.write(html_content)
            
            # Open in browser and ask user to select location
            webbrowser.open("select_location.html")
            
        except Exception as e:
            print(f"Error getting location: {e}")
            messagebox.showerror(
                "Location Error",
                "Could not get location. Please try again."
            )

    def get_coordinates_from_address(self, address):
        """Convert address to coordinates"""
        try:
            location = self.geolocator.geocode(address)
            if location:
                return (location.latitude, location.longitude)
        except Exception as e:
            print(f"Error getting coordinates: {e}")
        return None

    def generate_map(self, pothole_locations):
        """Generate HTML map with pothole markers"""
        try:
            if not pothole_locations:
                print("No pothole locations provided")
                return None

            # Create map centered on first pothole with valid coordinates
            valid_locations = []
            for loc in pothole_locations:
                try:
                    lat = float(loc['latitude'])
                    lng = float(loc['longitude'])
                    valid_locations.append({
                        'latitude': lat,
                        'longitude': lng,
                        'severity': loc['severity'],
                        'timestamp': loc['timestamp'],
                        'num_potholes': loc['num_potholes']
                    })
                except (ValueError, TypeError) as e:
                    print(f"Skipping invalid location data: {e}")
                    continue

            if not valid_locations:
                print("No valid locations found")
                return None

            # Calculate center coordinates
            center_lat = sum(loc['latitude'] for loc in valid_locations) / len(valid_locations)
            center_lng = sum(loc['longitude'] for loc in valid_locations) / len(valid_locations)
            
            # Create map
            m = folium.Map(location=[center_lat, center_lng], zoom_start=13)

            # Add markers for each pothole
            for loc in valid_locations:
                try:
                    color = 'red' if loc['severity'] == 'high' else 'orange' if loc['severity'] == 'medium' else 'green'
                    folium.CircleMarker(
                        [loc['latitude'], loc['longitude']],
                        radius=8,
                        popup=f"""
                            <b>Severity:</b> {loc['severity']}<br>
                            <b>Count:</b> {loc['num_potholes']}<br>
                            <b>Date:</b> {loc['timestamp']}
                        """,
                        color=color,
                        fill=True
                    ).add_to(m)
                except Exception as e:
                    print(f"Error adding marker: {e}")
                    continue

            # Save map
            map_file = f"pothole_map_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            m.save(map_file)
            return map_file
        except Exception as e:
            print(f"Error generating map: {e}")
            print(f"Pothole locations data: {pothole_locations}")
            return None

    def generate_heatmap(self, pothole_locations):
        """Generate heatmap of pothole concentrations"""
        try:
            if not pothole_locations:
                print("No pothole locations provided")
                return None

            # Create base map
            center_lat = sum(loc['latitude'] for loc in pothole_locations) / len(pothole_locations)
            center_lng = sum(loc['longitude'] for loc in pothole_locations) / len(pothole_locations)
            m = folium.Map(location=[center_lat, center_lng], zoom_start=13)

            # Prepare heatmap data
            heat_data = [
                [loc['latitude'], loc['longitude'], loc['num_potholes']] 
                for loc in pothole_locations
            ]

            # Add heatmap layer
            plugins.HeatMap(heat_data).add_to(m)

            # Save map
            map_file = f"pothole_heatmap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            m.save(map_file)
            return map_file
        except Exception as e:
            print(f"Error generating heatmap: {e}")
            return None

    def plan_route(self, start_address, end_address):
        """Plan route avoiding high pothole concentration areas"""
        try:
            print(f"Finding route from '{start_address}' to '{end_address}'...")
            
            # Convert addresses to coordinates
            start_coords = self.get_coordinates_from_address(start_address)
            if not start_coords:
                print(f"Could not find coordinates for start address: {start_address}")
                return None
            
            end_coords = self.get_coordinates_from_address(end_address)
            if not end_coords:
                print(f"Could not find coordinates for end address: {end_address}")
                return None

            print(f"Start coordinates: {start_coords}")
            print(f"End coordinates: {end_coords}")

            # Create map
            m = folium.Map(location=start_coords, zoom_start=13)

            # Add markers for start and end
            folium.Marker(
                start_coords,
                popup='Start',
                icon=folium.Icon(color='green', icon='info-sign')
            ).add_to(m)
            
            folium.Marker(
                end_coords,
                popup='End',
                icon=folium.Icon(color='red', icon='info-sign')
            ).add_to(m)

            # Get route from OpenStreetMap
            url = f"http://router.project-osrm.org/route/v1/driving/{start_coords[1]},{start_coords[0]};{end_coords[1]},{end_coords[0]}?overview=full&geometries=polyline"
            response = requests.get(url)
            if response.status_code == 200:
                route = polyline.decode(response.json()['routes'][0]['geometry'])
                folium.PolyLine(route, weight=2, color='blue', opacity=0.8).add_to(m)

            # Save map
            map_file = f"route_map_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            m.save(map_file)
            return map_file
        except Exception as e:
            print(f"Error planning route: {e}")
            return None 