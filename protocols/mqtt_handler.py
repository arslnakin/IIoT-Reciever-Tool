from protocols.base_handler import ProtocolHandlerBase
import paho.mqtt.client as mqtt
from PyQt6.QtCore import QThread, pyqtSignal, QObject
import time

# Worker class to handle MQTT communication in a separate thread
class MqttWorker(QObject):
    # Signals to communicate with the main thread (MqttHandler)
    status_changed = pyqtSignal(str, str)  # status_message, color
    message_received = pyqtSignal(str, str, str) # timestamp, topic, payload

    def __init__(self, broker, port, user, pwd):
        super().__init__()
        self.broker = broker
        self.port = port
        self.user = user
        self.pwd = pwd
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message

    def connect_to_broker(self):
        """Initiates connection to the MQTT broker."""
        try:
            if self.user:
                self.client.username_pw_set(self.user, self.pwd)
            self.status_changed.emit(f"{self.broker}:{self.port} adresine bağlanılıyor...", "orange")
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()  # Start network loop in a background thread
        except Exception as e:
            self.status_changed.emit(f"Bağlantı hatası: {e}", "red")

    def on_connect(self, client, userdata, flags, reason_code, properties):
        """Callback for when the client connects to the broker."""
        if reason_code == 0:
            self.status_changed.emit("Bağlandı", "green")
            # Re-subscribe to topics if any, or subscribe to a default topic
            self.subscribe("#") # Subscribe to all topics by default
        else:
            self.status_changed.emit(f"Bağlantı başarısız: {mqtt.connack_string(reason_code)}", "red")

    def on_disconnect(self, client, userdata, reason_code, properties):
        """Callback for when the client disconnects from the broker."""
        self.status_changed.emit("Bağlantı kesildi", "red")
        self.client.loop_stop()

    def on_message(self, client, userdata, msg):
        """Callback for when a message is received from the broker."""
        try:
            payload = msg.payload.decode('utf-8')
        except UnicodeDecodeError:
            payload = f"[Binary Data: {len(msg.payload)} bytes]"
        
        timestamp = time.strftime('%H:%M:%S', time.localtime())
        self.message_received.emit(timestamp, msg.topic, payload)

    def subscribe(self, topic):
        """Subscribes to a given topic."""
        if self.client.is_connected():
            self.client.subscribe(topic)
            print(f"Subscribed to {topic}")

    def publish(self, topic, payload):
        """Publishes a message to a given topic."""
        if self.client.is_connected():
            self.client.publish(topic, payload)
            print(f"Published to {topic}: {payload}")

    def disconnect_from_broker(self):
        """Disconnects from the broker."""
        self.client.disconnect()
        self.client.loop_stop()

class MqttHandler(ProtocolHandlerBase):
    def __init__(self, ui):
        super().__init__(ui)
        self.worker = None
        self.thread = None
        self._setup_table()
        self._connect_signals()

    def _setup_table(self):
        """Sets up the table for displaying MQTT messages."""
        tw = self.ui.mqttMessagesTable
        tw.setColumnCount(3)
        tw.setHorizontalHeaderLabels(["Zaman", "Topic", "Payload"])
        tw.setColumnWidth(0, 80)
        tw.setColumnWidth(1, 200)
        # Make the last column stretch
        tw.horizontalHeader().setStretchLastSection(True)

    def _connect_signals(self):
        """Connects UI signals to handler methods."""
        self.ui.mqttConnectBtn.clicked.connect(self.toggle_connection)
        self.ui.mqttSubscribeBtn.clicked.connect(self.subscribe_topic)
        self.ui.mqttPublishBtn.clicked.connect(self.publish_message)

    def toggle_connection(self):
        """Connects or disconnects based on the current state."""
        if self.worker:
            self.disconnect()
        else:
            self.connect()

    def connect(self):
        """Creates the worker and connects to the MQTT broker."""
        broker = self.ui.mqttBrokerEdit.text()
        try:
            port = int(self.ui.mqttPortEdit.text())
        except ValueError:
            self.log_message.emit("Geçersiz Port numarası.")
            return
        
        user = self.ui.mqttUserEdit.text()
        pwd = self.ui.mqttPassEdit.text()

        self.thread = QThread()
        self.worker = MqttWorker(broker, port, user, pwd)
        self.worker.moveToThread(self.thread)

        # Connect worker signals to handler slots
        self.worker.status_changed.connect(self.update_status)
        self.worker.message_received.connect(self.add_message_to_table)
        self.thread.started.connect(self.worker.connect_to_broker)

        self.thread.start()
        self.ui.mqttConnectBtn.setText("Bağlantıyı Kes")

    def disconnect(self):
        """Stops the worker and disconnects from the broker."""
        if self.worker:
            self.worker.disconnect_from_broker()
        if self.thread:
            self.thread.quit()
            self.thread.wait()
        self.worker = None
        self.thread = None
        self.update_status("Bağlantı kesildi", "red")
        self.ui.mqttConnectBtn.setText("Bağlan")

    def subscribe_topic(self):
        """Subscribes to the topic specified in the UI."""
        if self.worker:
            topic = self.ui.mqttSubscribeTopicEdit.text()
            if topic:
                self.worker.subscribe(topic)
                self.log_message.emit(f"'{topic}' konusuna abone olundu.")
            else:
                self.log_message.emit("Abonelik için bir konu (topic) girin.")

    def publish_message(self):
        """Publishes the message specified in the UI."""
        if self.worker:
            topic = self.ui.mqttPublishTopicEdit.text()
            payload = self.ui.mqttPublishPayloadEdit.text()
            if topic:
                self.worker.publish(topic, payload)
                self.log_message.emit(f"'{topic}' konusuna mesaj gönderildi.")
            else:
                self.log_message.emit("Yayınlamak için bir konu (topic) girin.")

    def update_status(self, message, color):
        """Updates the status label in the UI."""
        self.log_message.emit(f"MQTT Durum: {message}")

    def add_message_to_table(self, timestamp, topic, payload):
        """Adds a new received message to the top of the table."""
        from PyQt6.QtWidgets import QTableWidgetItem
        tw = self.ui.mqttMessagesTable
        tw.insertRow(0)
        tw.setItem(0, 0, QTableWidgetItem(timestamp))
        tw.setItem(0, 1, QTableWidgetItem(topic))
        tw.setItem(0, 2, QTableWidgetItem(payload))

    def get_status(self) -> str:
        """Returns the current connection status."""
        return "connected" if self.worker and self.worker.client.is_connected() else "disconnected"

    def serialize(self) -> dict:
        """Serializes MQTT settings for saving."""
        return {
            "broker": self.ui.mqttBrokerEdit.text(),
            "port": self.ui.mqttPortEdit.text(),
            "user": self.ui.mqttUserEdit.text(),
            "pass": self.ui.mqttPassEdit.text(),
            "sub_topic": self.ui.mqttSubscribeTopicEdit.text(),
            "pub_topic": self.ui.mqttPublishTopicEdit.text(),
        }

    def deserialize(self, data: dict):
        """Loads MQTT settings into the UI."""
        self.ui.mqttBrokerEdit.setText(data.get("broker", "mqtt.eclipseprojects.io"))
        self.ui.mqttPortEdit.setText(data.get("port", "1883"))
        self.ui.mqttUserEdit.setText(data.get("user", ""))
        self.ui.mqttPassEdit.setText(data.get("pass", ""))
        self.ui.mqttSubscribeTopicEdit.setText(data.get("sub_topic", "#"))
        self.ui.mqttPublishTopicEdit.setText(data.get("pub_topic", "test/topic"))