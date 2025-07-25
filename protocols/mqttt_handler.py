from PyQt6.QtCore import QThread, pyqtSignal
from protocols.base_handler import ProtocolHandlerBase
import paho.mqtt.client as mqtt

class MqttWorker(QThread):
    message_received = pyqtSignal(str, str)
    connected = pyqtSignal(bool)

    def __init__(self, broker, port, user, pwd):
        super().__init__()
        self.broker, self.port, self.user, self.pwd = broker, port, user, pwd
        self.client = mqtt.Client()
        if user:
            self.client.username_pw_set(user, pwd)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.running = False

    def _on_connect(self, client, userdata, flags, rc):
        self.connected.emit(rc == 0)

    def _on_message(self, client, userdata, msg):
        self.message_received.emit(msg.topic, msg.payload.decode())

    def run(self):
        self.running = True
        self.client.connect(self.broker, self.port, 60)
        self.client.loop_start()
        while self.running:
            self.msleep(100)
        self.client.loop_stop()
        self.client.disconnect()

    def stop(self):
        self.running = False

    def publish(self, topic, payload):
        self.client.publish(topic, payload)

    def subscribe(self, topic):
        self.client.subscribe(topic)

class MqttHandler(ProtocolHandlerBase):
    def __init__(self, ui):
        super().__init__(ui)
        self.worker = None
        self._connect_signals()

    def _connect_signals(self):
        self.ui.mqttConnectBtn.clicked.connect(self.toggle_connection)
        self.ui.mqttPubBtn.clicked.connect(self.publish)
        self.ui.mqttSubBtn.clicked.connect(self.subscribe)

    def toggle_connection(self):
        if self.worker and self.worker.isRunning():
            self.disconnect()
        else:
            self.connect()

    def connect(self):
        broker = self.ui.mqttBrokerEdit.text()
        port   = int(self.ui.mqttPortEdit.text())
        user   = self.ui.mqttUserEdit.text()
        pwd    = self.ui.mqttPassEdit.text()
        self.worker = MqttWorker(broker, port, user, pwd)
        self.worker.connected.connect(lambda ok: self.log_message.emit("MQTT bağlandı." if ok else "MQTT bağlantı hatası."))
        self.worker.connected.connect(lambda ok: self.ui.mqttConnectBtn.setText("Bağlantıyı Kes" if ok else "Bağlan"))
        self.worker.message_received.connect(self.on_message)
        self.worker.start()

    def disconnect(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
            self.worker = None
        self.ui.mqttConnectBtn.setText("Bağlan")
        self.log_message.emit("MQTT bağlantısı kesildi.")

    def publish(self):
        topic   = self.ui.mqttPubTopicEdit.text()
        payload = self.ui.mqttPubPayloadEdit.toPlainText()
        if self.worker:
            self.worker.publish(topic, payload)
            self.log_message.emit(f"MQTT Publish: {topic} -> {payload}")

    def subscribe(self):
        topic = self.ui.mqttSubTopicEdit.text()
        if self.worker:
            self.worker.subscribe(topic)
            self.log_message.emit(f"MQTT Subscribe: {topic}")

    def on_message(self, topic, payload):
        self.ui.mqttMsgList.addItem(f"{topic}: {payload}")
        self.ui.mqttMsgList.scrollToBottom()

    def get_status(self) -> str:
        return "connected" if self.worker and self.worker.isRunning() else "disconnected"

    def serialize(self) -> dict:
        return {
            "broker": self.ui.mqttBrokerEdit.text(),
            "port": self.ui.mqttPortEdit.text(),
            "user": self.ui.mqttUserEdit.text(),
            "pass": self.ui.mqttPassEdit.text()
        }

    def deserialize(self, data: dict):
        self.ui.mqttBrokerEdit.setText(data.get("broker", "localhost"))
        self.ui.mqttPortEdit.setText(data.get("port", "1883"))
        self.ui.mqttUserEdit.setText(data.get("user", ""))
        self.ui.mqttPassEdit.setText(data.get("pass", ""))