import tkinter as tk
import customtkinter
import imageDetector
import videoDetector
from tkinter import Label, filedialog as fd, simpledialog, messagebox
from tkinter.messagebox import showinfo
from location_services import LocationService
from database_manager import DatabaseManager
from geopy.geocoders import Nominatim
from datetime import datetime
import pytz
import folium
import webbrowser
import csv
import requests
import polyline
from tkinter import ttk
import threading

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = "7781878675:AAHzuvrHqrWAhZ3bneaP4USS5uog68KfJ5U"  # Replace with your bot token
TELEGRAM_CHAT_ID = "5018333444"  # Replace with your chat ID

def send_to_telegram(message, image_path=None):
    """Send a message and optionally an image to Telegram"""
    try:
        if image_path:
            # Send image with caption
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
            files = {"photo": open(image_path, "rb")}
            data = {"chat_id": TELEGRAM_CHAT_ID, "caption": message}
            response = requests.post(url, files=files, data=data)
        else:
            # Send text message
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
            response = requests.post(url, data=data)

        if response.status_code == 200:
            print("Message sent to Telegram successfully!")
        else:
            print(f"Failed to send message to Telegram. Error: {response.text}")
    except Exception as e:
        print(f"Error sending to Telegram: {e}")

customtkinter.set_appearance_mode("System") 
customtkinter.set_default_color_theme("dark-blue")  


class PotholeDetectorApp:
    def __init__(self, root):
        self.root = root
        self.db = DatabaseManager()
        self.location_service = LocationService()
        self.setup_ui()

    def setup_ui(self):
        self.root.title('Potholes Detection')
        self.root.resizable(False, False)
        self.root.geometry('400x300')

        Label(self.root, text="Select Image or Video to Identify Pothole", font=("poppins", 16)).pack(pady=15)

        buttons = [
            ("Image", self.select_image_file),
            ("Video", self.select_video_file),
            ("Live Camera", self.live_camera),
            ("View Pothole Summary", self.view_pothole_summary),
            ("Plan Route", self.plan_route),
        ]

        for text, command in buttons:
            customtkinter.CTkButton(self.root, text=text, command=command).pack(pady=5)

    def select_image_file(self):
        filename = fd.askopenfilename(title='Open Image File', filetypes=[('Image files', '*.jpg')])
        if filename:
            self.process_detection(imageDetector.detectPotholeonImage, filename, "Image File")

    def select_video_file(self):
        filename = fd.askopenfilename(title='Open Video File', filetypes=[('Video files', '*.mp4')])
        if filename:
            self.process_detection(videoDetector.detectPotholeonVideo, filename, "Video File")

    def live_camera(self):
        self.process_detection(videoDetector.detectPotholeonVideo, 0, "Real-time Camera")

    def process_detection(self, detection_method, source, source_label):
        if detection_method == videoDetector.detectPotholeonVideo:
            potholes_detected = detection_method(source, self.save_location_data) or 0
        else:
            potholes_detected = detection_method(source) or 0

        severity = self.determine_severity(potholes_detected)
        
        # Send Telegram notification about pothole detection
        message = f"🚧 Pothole Alert!\n\nDetected {potholes_detected} potholes from {source_label}\nSeverity: {severity}"
        threading.Thread(target=send_to_telegram, args=(message,)).start()
        
        # First show the map for coordinate selection
        self.location_service.get_current_location()
        
        # Get coordinates from the map
        coords = simpledialog.askstring("Input", "Enter the coordinates shown on the map (latitude,longitude):")
        if coords:
            self.submit_coordinates(coords, potholes_detected, source_label, severity)

    def submit_coordinates(self, coords, num_potholes, source, severity):
        try:
            latitude, longitude = map(float, coords.split(','))
            geolocator = Nominatim(user_agent="pothole_detector")
            location = geolocator.reverse((latitude, longitude), exactly_one=True)

            address = location.address if location else "Unknown Location"
            showinfo("Coordinates Submitted", f"Entered: {coords}\nAddress: {address}")

            self.save_location_data(coords, address, num_potholes, source, severity)
        except ValueError:
            showinfo("Input Error", "Invalid coordinate format.")
        except Exception as e:
            showinfo("Error", f"An error occurred: {e}")

    def save_location_data(self, coords, address, num_potholes, source, severity):
        latitude, longitude = map(float, coords.split(','))
        current_time = datetime.now(pytz.timezone('Asia/Kolkata'))

        self.db.save_location(latitude, longitude, address, num_potholes, source, severity, current_time)
        
        # Send Telegram notification with location details
        message = f"📍 New Pothole Location Recorded\n\n"
        message += f"Address: {address}\n"
        message += f"Coordinates: {coords}\n"
        message += f"Source: {source}\n"
        message += f"Time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}"
        
        threading.Thread(target=send_to_telegram, args=(message,)).start()

    def view_pothole_summary(self):
        data = self.db.get_all_potholes()
        if not data:
            showinfo("No Data", "No pothole data available.")
            return

        # Create a new window to display the summary
        summary_window = tk.Toplevel(self.root)
        summary_window.title("Pothole Summary")

        # Create a Treeview to display the data
        tree = ttk.Treeview(summary_window, columns=("Timestamp", "Pothole Count", "Coordinates", "Source", "Severity"), show='headings')
        tree.heading("Timestamp", text="Timestamp")
        tree.heading("Pothole Count", text="Pothole Count")
        tree.heading("Coordinates", text="Coordinates")
        tree.heading("Source", text="Source")
        tree.heading("Severity", text="Severity")
        tree.pack(expand=True, fill='both')

        # Insert data into the Treeview
        for record in data:
            tree.insert("", "end", values=record)

        # Add a button to export the summary to CSV
        export_button = customtkinter.CTkButton(summary_window, text='Export to CSV', command=self.export_summary_to_csv)
        export_button.pack(pady=10)

        # Add a button to reset the database
        reset_button = customtkinter.CTkButton(summary_window, text='Reset Database', command=self.reset_database)
        reset_button.pack(pady=10)

        # Add a button to generate the map
        generate_map_button = customtkinter.CTkButton(summary_window, text='Generate Map', command=self.generate_map)
        generate_map_button.pack(pady=10)

    def export_summary_to_csv(self):
        data = self.db.get_all_potholes()
        if not data:
            showinfo("No Data", "No pothole data available to export.")
            return

        with open("pothole_summary.csv", "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["Timestamp", "Pothole Count", "Coordinates", "Source", "Severity"])
            writer.writerows(data)

        showinfo("Export Successful", "Pothole summary exported to 'pothole_summary.csv'.")

    def plan_route(self):
        route_window = tk.Toplevel(self.root)
        route_window.title("Plan Route")

        # Add JavaScript function to handle route drawing
        html_content = """
        <script>
        function draw_route(start_lat, start_lng, end_lat, end_lng) {
            clearRoute();
            document.getElementById('status').innerHTML = 'Fetching route...';
            document.getElementById('status').className = '';
            
            // Ensure coordinates are properly formatted
            start_lat = parseFloat(start_lat.toFixed(6));
            start_lng = parseFloat(start_lng.toFixed(6));
            end_lat = parseFloat(end_lat.toFixed(6));
            end_lng = parseFloat(end_lng.toFixed(6));

            // Calculate straight-line distance in meters
            const R = 6371e3;
            const φ1 = start_lat * Math.PI/180;
            const φ2 = end_lat * Math.PI/180;
            const Δφ = (end_lat-start_lat) * Math.PI/180;
            const Δλ = (end_lng-start_lng) * Math.PI/180;
            const a = Math.sin(Δφ/2) * Math.sin(Δφ/2) +
                    Math.cos(φ1) * Math.cos(φ2) *
                    Math.sin(Δλ/2) * Math.sin(Δλ/2);
            const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
            const distance = R * c;

            // If points are too close (less than 50 meters), draw a straight line
            if (distance < 50) {
                drawDirectLine(start_lat, start_lng, end_lat, end_lng, distance);
                return;
            }

            // Try OSRM routing service
            const osrmUrl = `https://router.project-osrm.org/route/v1/driving/${start_lng},${start_lat};${end_lng},${end_lat}?overview=full&geometries=geojson`;
            
            fetch(osrmUrl)
                .then(response => response.json())
                .then(data => {
                    if (!data.routes || !data.routes[0]) {
                        throw new Error('No route found');
                    }

                    const route = data.routes[0];
                    const coordinates = route.geometry.coordinates;
                    
                    // Convert coordinates from [lng, lat] to [lat, lng] for Leaflet
                    const points = coordinates.map(coord => [coord[1], coord[0]]);
                    
                    // Draw the route
                    routeLayer = L.polyline(points, {
                        color: 'blue',
                        weight: 5,
                        opacity: 0.7
                    }).addTo(map);

                    // Add markers
                    addMarkers(start_lat, start_lng, end_lat, end_lng);

                    // Fit the map to show the entire route
                    map.fitBounds(routeLayer.getBounds(), { padding: [50, 50] });

                    // Show route information
                    document.getElementById('status').innerHTML = `
                        <div class="success">Route found!</div>
                    `;
                })
                .catch(error => {
                    console.error('Error:', error);
                    drawDirectLine(start_lat, start_lng, end_lat, end_lng, distance);
                });
        }

        function drawDirectLine(start_lat, start_lng, end_lat, end_lng, distance) {
            routeLayer = L.polyline([[start_lat, start_lng], [end_lat, end_lng]], {
                color: 'blue',
                weight: 5,
                opacity: 0.7,
                dashArray: '10, 10'
            }).addTo(map);

            addMarkers(start_lat, start_lng, end_lat, end_lng);

            // Fit bounds to show both points
            var bounds = L.latLngBounds([[start_lat, start_lng], [end_lat, end_lng]]);
            map.fitBounds(bounds, { padding: [50, 50] });

            document.getElementById('status').innerHTML = `
                <div class="warning">Showing direct line between points</div>
            `;
        }

        function addMarkers(start_lat, start_lng, end_lat, end_lng) {
            // Add start marker
            L.marker([start_lat, start_lng], {
                title: 'Start Point',
                icon: L.icon({
                    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png',
                    iconSize: [25, 41],
                    iconAnchor: [12, 41],
                    popupAnchor: [1, -34]
                })
            }).addTo(map);
            
            // Add end marker
            L.marker([end_lat, end_lng], {
                title: 'End Point',
                icon: L.icon({
                    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
                    iconSize: [25, 41],
                    iconAnchor: [12, 41],
                    popupAnchor: [1, -34]
                })
            }).addTo(map);
        }

        function clearRoute() {
            if (routeLayer) {
                map.removeLayer(routeLayer);
                routeLayer = null;
            }
        }

        function tryFetchRoute(x1, y1, x2, y2) {
            return fetch(`http://router.project-osrm.org/route/v1/driving/${x1},${y1};${x2},${y2}?overview=full&geometries=polyline`)
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Network response was not ok');
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.code !== 'Ok' || !data.routes || !data.routes[0]) {
                        throw new Error('No route found');
                    }
                    var route = polyline.decode(data.routes[0].geometry);
                    routeLayer = L.polyline(route, {color: 'blue', weight: 5}).addTo(map);
                    document.getElementById('status').innerHTML = 'Route drawn successfully!';
                    document.getElementById('status').className = 'success';
                    
                    // Fit the map to show the entire route
                    map.fitBounds(routeLayer.getBounds(), {padding: [50, 50]});
                });
        }
        </script>
        """

        buttons = [
            ("Location Name", self.get_location_names),
            ("Coordinates", self.get_coordinates_input),
            ("Manual Click", self.open_manual_click_map),
        ]

        for text, command in buttons:
            customtkinter.CTkButton(route_window, text=text, command=command).pack(pady=10)

    def get_location_names(self):
        start_location = simpledialog.askstring("Input", "Enter the start location name:")
        end_location = simpledialog.askstring("Input", "Enter the end location name:")

        if start_location and end_location:
            start_coords = self.location_service.get_coordinates_from_address(start_location)
            end_coords = self.location_service.get_coordinates_from_address(end_location)

            if start_coords and end_coords:
                self.draw_route(f"{start_coords[0]},{start_coords[1]}", f"{end_coords[0]},{end_coords[1]}")
            else:
                showinfo("Error", "Could not find coordinates for the provided location names.")
        else:
            showinfo("Input Error", "Please enter both start and end location names.")

    def get_coordinates_input(self):
        # First show the map for coordinate selection
        self.location_service.get_current_location()
        
        # Then get the coordinates
        start_coords = simpledialog.askstring("Input", "Enter start coordinates (latitude,longitude):")
        if start_coords:
            end_coords = simpledialog.askstring("Input", "Enter end coordinates (latitude,longitude):")
            if end_coords:
                try:
                    # Validate coordinates format
                    start_lat, start_lng = map(float, start_coords.split(','))
                    end_lat, end_lng = map(float, end_coords.split(','))
                    # Draw the route on a new map
                    self.draw_route(start_coords, end_coords)
                    # Open the route map in browser
                    webbrowser.open("route_map.html")
                except ValueError:
                    showinfo("Input Error", "Invalid coordinate format. Please enter coordinates as 'latitude,longitude'")

    def draw_route(self, start_coords, end_coords):
        start_lat, start_lng = map(float, start_coords.split(','))
        end_lat, end_lng = map(float, end_coords.split(','))

        print(f"Start Coordinates: {start_lat}, {start_lng}")
        print(f"End Coordinates: {end_lat}, {end_lng}")

        # Create a folium map centered on Karnataka
        m = folium.Map(location=[15.3173, 75.7139], zoom_start=7)

        # Add zoom controls
        folium.plugins.MousePosition().add_to(m)
        folium.plugins.Fullscreen().add_to(m)

        # Add markers for start and end
        folium.Marker(
            location=[start_lat, start_lng],
            popup='Start',
            icon=folium.Icon(color='green')
        ).add_to(m)

        folium.Marker(
            location=[end_lat, end_lng],
            popup='End',
            icon=folium.Icon(color='red')
        ).add_to(m)

        # Get pothole data
        pothole_data = self.db.get_all_potholes()
        route_potholes = []
        total_potholes = 0
        high_severity_count = 0

        # Get route from OpenStreetMap
        url = f"http://router.project-osrm.org/route/v1/driving/{start_lng},{start_lat};{end_lng},{end_lat}?overview=full&geometries=polyline"
        print(f"Requesting route from URL: {url}")  # Debugging output
        response = requests.get(url)
        if response.status_code == 200:
            route = polyline.decode(response.json()['routes'][0]['geometry'])
            route_line = folium.PolyLine(route, weight=5, color='blue', opacity=0.7).add_to(m)

            # Check for potholes near the route
            for record in pothole_data:
                lat, lng = map(float, record[2].split(','))
                severity = record[4]
                count = record[1]
                
                # Calculate distance from pothole to route
                min_distance = float('inf')
                for route_point in route:
                    # Calculate distance in kilometers
                    distance = ((lat - route_point[0])**2 + (lng - route_point[1])**2)**0.5 * 111
                    min_distance = min(min_distance, distance)
                
                # If pothole is within 500 meters of the route
                if min_distance < 0.5:  # 0.5 km = 500 meters
                    route_potholes.append({
                        'lat': lat,
                        'lng': lng,
                        'count': count,
                        'severity': severity,
                        'distance': min_distance
                    })
                    total_potholes += count
                    if severity == 'High':
                        high_severity_count += 1
                    
                    # Add pothole marker with warning
                    color = 'red' if severity == 'High' else 'orange' if severity == 'Moderate' else 'green'
                    folium.CircleMarker(
                        location=[lat, lng],
                        radius=8,
                        popup=f'Potholes: {count}<br>Severity: {severity}<br>Distance from route: {min_distance:.1f}km',
                        color=color,
                        fill=True,
                        fill_opacity=0.8
                    ).add_to(m)

            # Save the map to an HTML file with fixed name
            map_file = "route_map.html"
            m.save(map_file)

            # Show warning message about potholes
            if route_potholes:
                warning_message = f"⚠️ Warning: Found {len(route_potholes)} pothole locations along the route!\n\n"
                warning_message += f"Total number of potholes: {total_potholes}\n"
                warning_message += f"High severity potholes: {high_severity_count}\n"
                warning_message += "Please drive carefully and avoid these areas if possible!"
                showinfo("Route Warning", warning_message)
                # Open the map after showing the warning
                webbrowser.open(map_file)
            else:
                showinfo("Route Info", "No potholes found along this route. Safe to proceed!")
                # Open the map after showing the info
                webbrowser.open(map_file)
        else:
            print(f"Error fetching route: {response.status_code}, {response.text}")  # Debugging output
            showinfo("Error", "Could not fetch the route. Please try again.")

    def open_manual_click_map(self):
        # Get pothole data from database
        pothole_data = self.db.get_all_potholes()
        
        # Convert pothole data to a JavaScript-friendly format
        pothole_data_js = []
        for record in pothole_data:
            try:
                lat, lng = map(float, record[2].split(','))
                pothole_data_js.append({
                    'lat': lat,
                    'lng': lng,
                    'count': record[1],
                    'severity': record[4]
                })
            except Exception as e:
                print(f"Error processing pothole record: {e}")
                continue
        
        # Create an HTML file for the map with manual click functionality
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Select Start and End Points</title>
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css"/>
            <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
            <style>
                html, body {
                    height: 100%;
                    margin: 0;
                    padding: 0;
                }
                #map { 
                    height: 100vh;
                    width: 100%;
                }
                #coordinates { 
                    position: absolute; 
                    bottom: 20px; 
                    left: 50%; 
                    transform: translateX(-50%);
                    background: white;
                    padding: 10px;
                    border-radius: 5px;
                    z-index: 1000;
                    max-width: 80%;
                    text-align: center;
                }
            </style>
        </head>
        <body>
            <div id="map"></div>
            <div id="coordinates">
                <div>Click on the map to select start and end points</div>
                <div id="status"></div>
            </div>
            <script>
                // Initialize map centered on Karnataka
                var map = L.map('map').setView([15.3173, 75.7139], 7);
                
                // Add tile layer
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    attribution: '© OpenStreetMap contributors'
                }).addTo(map);

                // Add zoom controls
                L.control.zoom({
                    position: 'bottomright',
                    zoomInTitle: 'Zoom in',
                    zoomOutTitle: 'Zoom out'
                }).addTo(map);

                // Add pothole markers
                var potholeData = """ + str(pothole_data_js) + """;
                potholeData.forEach(function(pothole) {
                    var color = pothole.severity === 'High' ? 'red' : 
                               pothole.severity === 'Moderate' ? 'orange' : 'green';
                    
                    L.circleMarker([pothole.lat, pothole.lng], {
                        radius: 8,
                        fillColor: color,
                        color: '#fff',
                        weight: 1,
                        opacity: 1,
                        fillOpacity: 0.8
                    }).bindPopup('Potholes: ' + pothole.count + '<br>Severity: ' + pothole.severity).addTo(map);
                });

                // Initialize variables
                var markers = [];
                var routeLayer = null;

                // Create marker icons
                var startIcon = L.icon({
                    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png',
                    iconSize: [25, 41],
                    iconAnchor: [12, 41],
                    popupAnchor: [1, -34]
                });

                var endIcon = L.icon({
                    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
                    iconSize: [25, 41],
                    iconAnchor: [12, 41],
                    popupAnchor: [1, -34]
                });

                // Handle map clicks
                map.on('click', function(e) {
                    if (markers.length < 2) {
                        // Create new marker
                        var marker = L.marker(e.latlng);
                        
                        // Add marker to map
                        marker.addTo(map);
                        
                        // Add to markers array
                        markers.push(marker);
                        
                        // Update coordinates display
                        var pointText = 'Point ' + markers.length + ': ' + e.latlng.lat.toFixed(6) + ', ' + e.latlng.lng.toFixed(6);
                        document.getElementById('coordinates').innerHTML = 
                            '<div>Click on the map to select start and end points</div>' +
                            '<div>' + pointText + '</div>' +
                            '<div id="status"></div>';
                    }
                    
                    if (markers.length === 2) {
                        var startCoords = markers[0].getLatLng();
                        var endCoords = markers[1].getLatLng();
                        draw_route(startCoords.lat, startCoords.lng, endCoords.lat, endCoords.lng);
                    }
                });

                // Handle right-click to clear
                map.on('contextmenu', function(e) {
                    markers.forEach(marker => map.removeLayer(marker));
                    markers = [];
                    if (routeLayer) {
                        map.removeLayer(routeLayer);
                        routeLayer = null;
                    }
                    document.getElementById('coordinates').innerHTML = 
                        '<div>Click on the map to select start and end points</div>' +
                        '<div id="status"></div>';
                });

                function draw_route(start_lat, start_lng, end_lat, end_lng) {
                    if (routeLayer) {
                        map.removeLayer(routeLayer);
                    }
                    
                    document.getElementById('status').innerHTML = 'Fetching route...';
                    
                    // Calculate distance
                    var start = L.latLng(start_lat, start_lng);
                    var end = L.latLng(end_lat, end_lng);
                    var distance = start.distanceTo(end);
                    
                    if (distance < 50) {
                        // Draw direct line for close points
                        routeLayer = L.polyline([[start_lat, start_lng], [end_lat, end_lng]], {
                            color: 'blue',
                            weight: 5,
                            opacity: 0.7,
                            dashArray: '10, 10'
                        }).addTo(map);
                        
                        document.getElementById('status').innerHTML = 'Showing direct line between points';
                    } else {
                        // Fetch route from OSRM
                        fetch(`https://router.project-osrm.org/route/v1/driving/${start_lng},${start_lat};${end_lng},${end_lat}?overview=full&geometries=geojson`)
                            .then(response => response.json())
                            .then(data => {
                                if (data.routes && data.routes[0]) {
                                    var coordinates = data.routes[0].geometry.coordinates;
                                    var points = coordinates.map(coord => [coord[1], coord[0]]);
                                    
                                    routeLayer = L.polyline(points, {
                                        color: 'blue',
                                        weight: 5,
                                        opacity: 0.7
                                    }).addTo(map);
                                    
                                    document.getElementById('status').innerHTML = 'Route found!';
                                } else {
                                    throw new Error('No route found');
                                }
                            })
                            .catch(error => {
                                console.error('Error:', error);
                                routeLayer = L.polyline([[start_lat, start_lng], [end_lat, end_lng]], {
                                    color: 'blue',
                                    weight: 5,
                                    opacity: 0.7,
                                    dashArray: '10, 10'
                                }).addTo(map);
                                
                                document.getElementById('status').innerHTML = 'Showing direct line between points';
                            });
                    }
                    
                    // Fit map to show the entire route
                    map.fitBounds(L.latLngBounds([start, end]), { padding: [50, 50] });
                }
            </script>
        </body>
        </html>
        """

        # Save the HTML content to a file
        with open("manual_click_map.html", "w", encoding='utf-8') as f:
            f.write(html_content)

        # Open the map in the default web browser
        try:
            webbrowser.open("manual_click_map.html", new=2)
        except Exception as e:
            showinfo("Error", f"Could not open map: {str(e)}")

    def determine_severity(self, num_potholes):
        return "None" if num_potholes == 0 else "Low" if num_potholes <= 2 else "Moderate" if num_potholes <= 5 else "High"

    def reset_database(self):
        if messagebox.askyesno("Confirm Reset", "Are you sure you want to reset the database?"):
            self.db.reset_database()
            showinfo("Database Reset", "The database has been reset.")

    def generate_map(self):
        pothole_locations = self.db.get_all_potholes()  # Retrieve all pothole records
        if not pothole_locations:
            showinfo("No Data", "No pothole data available to display on the map.")
            return

        # Create a folium map centered on Karnataka
        m = folium.Map(location=[15.3173, 75.7139], zoom_start=7)

        # Add markers for each pothole
        for record in pothole_locations:
            lat, lng = map(float, record[2].split(','))
            folium.Marker(
                location=[lat, lng],
                popup=f"Count: {record[1]}<br>Severity: {record[4]}",
                icon=folium.Icon(color='red' if record[4] == 'High' else 'orange' if record[4] == 'Medium' else 'green')
            ).add_to(m)

        # Save the map to an HTML file
        map_file = "pothole_map.html"
        m.save(map_file)

        # Open the map in the default web browser
        webbrowser.open(map_file)


if __name__ == "__main__":
    root = customtkinter.CTk()
    app = PotholeDetectorApp(root)
root.mainloop()