import sys
import json
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QFileDialog, QMessageBox)
from PyQt6 import uic

from protocols.modbus_handler import ModbusHandler
from protocols.mqtt_handler import MqttHandler
from protocols.opc_ua_handler import OpcUaHandler

Ui_MainWindow, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "mainwindow.ui"))

class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        # Protokol handler'ları
        self.modbus_handler = ModbusHandler(self)
        self.mqtt_handler   = MqttHandler(self)
        self.opcua_handler  = OpcUaHandler(self)

        # Menü aksiyonları
        self.actionSave.triggered.connect(self.save_config)
        self.actionLoad.triggered.connect(self.load_config)

        # Log fonksiyonu
        self.modbus_handler.log_message.connect(self.append_log)
        self.mqtt_handler.log_message.connect(self.append_log)
        self.opcua_handler.log_message.connect(self.append_log)

    def append_log(self, text):
        self.logEdit.append(text)

    # ---------- Konfigürasyon ----------
    def save_config(self):
        file, _ = QFileDialog.getSaveFileName(self, "Konfigürasyon Kaydet", "", "JSON (*.json)")
        if file:
            cfg = {
                "modbus": self.modbus_handler.serialize(),
                "mqtt"  : self.mqtt_handler.serialize(),
                "opcua" : self.opcua_handler.serialize()
            }
            with open(file, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
            QMessageBox.information(self, "Bilgi", "Ayarlar kaydedildi.")

    def load_config(self):
        file, _ = QFileDialog.getOpenFileName(self, "Konfigürasyon Aç", "", "JSON (*.json)")
        if file and os.path.isfile(file):
            with open(file, encoding="utf-8") as f:
                cfg = json.load(f)
            self.modbus_handler.deserialize(cfg.get("modbus", {}))
            self.mqtt_handler.deserialize(cfg.get("mqtt", {}))
            self.opcua_handler.deserialize(cfg.get("opcua", {}))
            QMessageBox.information(self, "Bilgi", "Ayarlar yüklendi.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())