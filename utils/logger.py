import csv
import time
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal, QThread

class DataLogger(QObject):
    log_message = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.filename = None
        self.file = None
        self.writer = None
        self.logging = False
        self.start_time = None

    def start(self, filename=None):
        if not filename:
            filename = f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        self.filename = filename
        try:
            self.file = open(self.filename, 'w', newline='', encoding='utf-8')
            self.writer = csv.writer(self.file)
            self.writer.writerow(["Timestamp", "Protocol", "Tag/Topic", "Value"])
            self.logging = True
            self.start_time = time.time()
            self.log_message.emit(f"Logging started: {self.filename}")
        except Exception as e:
            self.log_message.emit(f"Failed to start logging: {e}")

    def stop(self):
        if self.logging:
            self.logging = False
            if self.file:
                self.file.close()
                self.file = None
            self.log_message.emit("Logging stopped.")

    def log(self, protocol, tag, value):
        if not self.logging:
            return
        
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            self.writer.writerow([timestamp, protocol, tag, value])
            self.file.flush() # Ensure data is written
        except Exception as e:
            self.log_message.emit(f"Write error: {e}")
