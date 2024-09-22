import sys
from PyQt5.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QWidget
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QTimer
import adafruit_dht
import board
import requests
import RPi.GPIO as GPIO
import serial
import smtplib
from twilio.rest import Client

# Set up DHT11 sensor on GPIO 4
dhtDevice = adafruit_dht.DHT11(board.D4)

# Set up rain sensor on GPIO 17
RAIN_SENSOR_PIN = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(RAIN_SENSOR_PIN, GPIO.IN)

# Set up serial communication for ESP32 (replace '/dev/serial0' with the correct port)
ser = serial.Serial('/dev/serial0', 115200, timeout=1)

# Define the Django server URL
django_server_url = "http://localhost:8000/weather_data/"

# Twilio account details (replace these with your own Twilio credentials)
account_sid = 'AC83afc1574e58a8393cc541901757186c'
auth_token = 'd044028471470efca56e02c6dcc7eef5'
twilio_phone_number = '+18482604772'
to_phone_number = '+923232124377'

# Email settings
smtp_server = 'smtp.gmail.com'
smtp_port = 587
email_address = 'codetitans@aptechgdn.net'
email_password = 'codetitans_techwiz'
to_email = 'shayan2209e@aptechgdn.net'

class WeatherApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.reading_active = False
        self.rain_alert_sent = False  # To avoid sending multiple alerts for rain start
        self.rain_end_alert_sent = False  # To send an alert when rain ends

    def initUI(self):
        # Set up window properties
        self.setWindowTitle("Weather Monitoring System")
        self.setGeometry(100, 100, 800, 600)

        # Set up the labels
        self.temp_label = QLabel("Temperature: -- °C", self)
        self.humidity_label = QLabel("Humidity: -- %", self)
        self.pressure_label = QLabel("Pressure: -- hPa", self)
        self.rain_label = QLabel("Rain Status: No rain detected", self)

        # Image label to display background
        self.image_label = QLabel(self)
        self.image_label.setPixmap(QPixmap("clear_sky.png"))
        self.image_label.setScaledContents(True)

        # Start and stop buttons
        self.start_button = QPushButton("Start", self)
        self.start_button.clicked.connect(self.start_reading)

        self.stop_button = QPushButton("Stop", self)
        self.stop_button.clicked.connect(self.stop_reading)

        # Layout setup
        layout = QVBoxLayout()
        layout.addWidget(self.temp_label)
        layout.addWidget(self.humidity_label)
        layout.addWidget(self.pressure_label)
        layout.addWidget(self.rain_label)
        layout.addWidget(self.image_label)
        layout.addWidget(self.start_button)
        layout.addWidget(self.stop_button)

        self.setLayout(layout)

        # Timer to refresh sensor data every 5 seconds
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_sensor_data)

    def start_reading(self):
        if not self.reading_active:
            self.reading_active = True
            self.timer.start(5000)  # Update every 5 seconds

    def stop_reading(self):
        self.reading_active = False
        self.timer.stop()

    def update_sensor_data(self):
        try:
            # Read temperature and humidity from DHT11
            temperature = dhtDevice.temperature
            humidity = dhtDevice.humidity

            # Read rain sensor
            rain_detected = GPIO.input(RAIN_SENSOR_PIN)

            # Read serial data from ESP32 (for pressure)
            esp_pressure = None
            if ser.in_waiting > 0:
                serial_data = ser.readline().decode('utf-8').rstrip()
                print(f"Received from ESP32: {serial_data}")
                # Assuming the ESP32 sends pressure in format: "Pressure <value>"
                if "Pressure" in serial_data:
                    esp_pressure = float(serial_data.split()[1])

            # Update the UI with sensor readings
            if temperature is not None and humidity is not None:
                self.temp_label.setText(f"Temperature: {temperature:.1f} °C")
                self.humidity_label.setText(f"Humidity: {humidity}%")

                if esp_pressure is not None:
                    self.pressure_label.setText(f"Pressure: {esp_pressure:.2f} hPa")

                if rain_detected == 0:  # Rain detected
                    self.rain_label.setText("Rain Status: Rain detected")
                    self.image_label.setPixmap(QPixmap("rain.png"))  # Change background to rain

                    if not self.rain_alert_sent:
                        self.send_alerts(temperature, humidity, esp_pressure, "Rain detected")
                        self.rain_alert_sent = True  # Mark that rain alert was sent
                        self.rain_end_alert_sent = False  # Reset rain end alert flag
                else:  # No rain detected
                    self.rain_label.setText("Rain Status: No rain detected")
                    self.image_label.setPixmap(QPixmap("clear_sky.png"))  # Change background to clear sky

                    if self.rain_alert_sent and not self.rain_end_alert_sent:  # Send rain over alert
                        self.send_alerts(temperature, humidity, esp_pressure, "Rain over")
                        self.rain_end_alert_sent = True  # Mark that rain end alert was sent
                        self.rain_alert_sent = False  # Reset rain start alert flag

                # Send data to Django server
                data = {
                    'temperature': temperature,
                    'humidity': humidity,
                    'pressure': esp_pressure if esp_pressure is not None else 0,  # Default to 0 if not received
                    'rain_detected': rain_detected
                }
                try:
                    response = requests.post(django_server_url, json=data, timeout=10)
                    response.raise_for_status()
                except requests.RequestException as req_error:
                    print(f"Request Error: {req_error}")

        except RuntimeError as error:
            print(f"RuntimeError: {error.args[0]}")

    def send_alerts(self, temperature, humidity, pressure, rain_status):
        alert_message = (
            f"Weather Alert:\n"
            f"Temperature: {temperature:.1f} °C\n"
            f"Humidity: {humidity}%\n"
            f"Pressure: {pressure:.2f} hPa\n"
            f"Rain Status: {rain_status}"
        )

        # Send SMS using Twilio
        try:
            client = Client(account_sid, auth_token)
            message = client.messages.create(
                body=alert_message,
                from_=twilio_phone_number,
                to=to_phone_number
            )
            print(f"SMS sent: {message.sid}")
        except Exception as e:
            print(f"Failed to send SMS: {e}")

        # Send email using SMTP
        try:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(email_address, email_password)
            subject = "Weather Alert"
            msg = f"Subject: {subject}\n\n{alert_message}"
            server.sendmail(email_address, to_email, msg)
            server.quit()
            print("Email sent successfully.")
        except Exception as e:
            print(f"Failed to send email: {e}")

# Main function to start the PyQt5 application
def main():
    app = QApplication(sys.argv)
    ex = WeatherApp()
    ex.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    try:
        main()
    finally:
        GPIO.cleanup()
