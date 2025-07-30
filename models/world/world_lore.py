import json

class WorldLore:
    """
    Represents the lore and environmental state of the world, including description, map data, time of day, and weather conditions.

    :param description: String description of the world.
    :type description: str
    :param map_data: JSON-serializable or binary data representing the world map.
    :type map_data: dict or bytes
    :param time_of_day: String indicating the time of day (e.g., "morning", "afternoon").
    :type time_of_day: str
    :param weather_conditions: String describing the current weather conditions (e.g., "sunny", "rainy").
    :type weather_conditions: str
    """

    def __init__(self, description, map_data, time_of_day, weather_conditions):
        """
        Initialize a WorldLore instance.

        :param description: String description of the world.
        :type description: str
        :param map_data: JSON-serializable or binary data representing the world map.
        :type map_data: dict or bytes
        :param time_of_day: String indicating the time of day (e.g., "morning", "afternoon").
        :type time_of_day: str
        :param weather_conditions: String describing the current weather conditions (e.g., "sunny", "rainy").
        :type weather_conditions: str
        """
        self.description = description
        self.map_data = map_data
        self.time_of_day = time_of_day
        self.weather_conditions = weather_conditions

    def update_weather(self, new_weather):
        """
        Update the weather in the world.

        :param new_weather: The new weather condition to set (e.g., "cloudy", "stormy").
        :type new_weather: str
        """
        self.weather_conditions = new_weather
        print(f"Weather updated to: {new_weather}")

    def update_time_of_day(self, new_time):
        """
        Update the time of day (morning, afternoon, evening, etc.).

        :param new_time: The new time of day to set (e.g., "evening", "night").
        :type new_time: str
        """
        self.time_of_day = new_time
        print(f"Time of day updated to: {new_time}")

    def describe_world(self):
        """
        Provide a textual description of the world.

        :return: A string summarizing the world's description, time of day, and weather conditions.
        :rtype: str
        """
        return f"World Description: {self.description}, Time: {self.time_of_day}, Weather: {self.weather_conditions}"

    def save_to_db(self, db_conn):
        """
        Save the world lore data to a database.

        :param db_conn: An open database connection object supporting the SQLite interface.
        :type db_conn: sqlite3.Connection
        """
        cursor = db_conn.cursor()
        cursor.execute('''
            INSERT INTO world_info (description, map, time_of_day, weather_conditions)
            VALUES (?, ?, ?, ?)
        ''', (self.description, json.dumps(self.map_data), self.time_of_day, self.weather_conditions))
        db_conn.commit()
