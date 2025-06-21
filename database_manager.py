import sqlite3

class DatabaseManager:
    def __init__(self, db_name='pothole_detection.db'):
        self.connection = sqlite3.connect(db_name)
        self.cursor = self.connection.cursor()
        self.create_table()

    def create_table(self):
        # Create a table to store pothole data
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS potholes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                address TEXT NOT NULL,
                num_potholes INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                source TEXT,
                severity TEXT
            )
        ''')
        self.connection.commit()
        print("Potholes table created or already exists.")

    def save_location(self, latitude, longitude, address, num_potholes, source, severity, timestamp):
        # Save the location data to the database
        query = '''
            INSERT INTO potholes (latitude, longitude, address, num_potholes, source, severity, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        '''
        self.cursor.execute(query, (latitude, longitude, address, num_potholes, source, severity, timestamp))
        self.connection.commit()

    def get_all_potholes(self):
        self.cursor.execute("SELECT timestamp, num_potholes, latitude || ', ' || longitude AS coordinates, source, severity FROM potholes ORDER BY timestamp DESC")
        return self.cursor.fetchall()  # Returns all records

    def create_view(self):
        # Create a view to summarize pothole counts by timestamp
        self.cursor.execute('''
            CREATE VIEW IF NOT EXISTS pothole_summary AS
            SELECT 
                DATE(timestamp) AS detection_date,
                SUM(num_potholes) AS total_potholes
            FROM 
                potholes
            GROUP BY 
                DATE(timestamp)
        ''')
        self.connection.commit()
        print("Pothole summary view created or already exists.")

    def get_pothole_summary(self):
        self.cursor.execute("SELECT DATE(timestamp), SUM(num_potholes) FROM potholes GROUP BY DATE(timestamp)")
        return self.cursor.fetchall()  # Returns a list of all records from the view

    def reset_database(self):
        self.cursor.execute("DROP TABLE IF EXISTS potholes")  # Drop the table if it exists
        self.create_table()  # Recreate the table
        print("Database reset: table recreated.")

    def close(self):
        self.connection.close()

    def print_all_records(self):
        self.cursor.execute("SELECT * FROM potholes")
        records = self.cursor.fetchall()
        for record in records:
            print(record) 