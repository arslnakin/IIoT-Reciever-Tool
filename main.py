import sys
import json
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QFileDialog, QMessageBox, QHeaderView)
from PyQt6 import uic, QtCore

from protocols.modbus_handler import ModbusHandler
from protocols.mqtt_handler import MqttHandler
from protocols.opc_ua_handler import OpcUaHandler
from protocols.scanner_handler import ScannerHandler
from protocols.s7_handler import S7Handler, S7TagHandler

Ui_MainWindow, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "mainwindow.ui"))

class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        
        # PyInstaller onefile fix for finding DLLs
        if getattr(sys, 'frozen', False):
            # If the application is run as a bundle, the PyInstaller bootloader
            # extends the sys module by a flag frozen=True and sets the app 
            # path into variable _MEIPASS'.
            application_path = sys._MEIPASS
            os.environ['PATH'] = application_path + os.pathsep + os.environ['PATH']
        
        self.setupUi(self)

        # Protokol handler'ları
        self.modbus_handler = ModbusHandler(self)
        self.mqtt_handler   = MqttHandler(self)
        self.opcua_handler  = OpcUaHandler(self)
        self.scanner_handler = ScannerHandler(self)
        self.s7_handler = S7Handler(self)
        self.s7_tag_handler = S7TagHandler(self)

        # OPC-UA Plotting
        self.opcua_plot_data_x = []
        self.opcua_plot_data_y = []
        self.opcua_plot_line = self.opcuaPlot.plot(pen='y')
        self.opcua_subscribed_node_id = None

        # Menü aksiyonları
        self.actionSave.triggered.connect(self.save_config)
        self.actionLoad.triggered.connect(self.load_config)

        # OPC-UA Buton Bağlantıları
        self.opcuaConnectBtn.clicked.connect(self.connect_opcua)
        self.opcuaCertBtn.clicked.connect(self.browse_opcua_cert)
        self.opcuaKeyBtn.clicked.connect(self.browse_opcua_key)
        self.opcuaTreeView.doubleClicked.connect(self.on_opcua_node_double_clicked)

        # Log fonksiyonu
        self.modbus_handler.log_message.connect(self.append_log)
        self.mqtt_handler.log_message.connect(self.append_log)
        self.opcua_handler.log_message.connect(self.append_log)
        self.scanner_handler.log_message.connect(self.append_log)
        self.s7_handler.log_message.connect(self.append_log)
        self.s7_tag_handler.log_message.connect(self.append_log)

        # UI Ayarları
        self.opcuaValueEdit.setReadOnly(True)

    def append_log(self, text):
        self.logEdit.append(text)

    # ---------- Konfigürasyon ----------
    def save_config(self):
        file, _ = QFileDialog.getSaveFileName(self, "Konfigürasyon Kaydet", "", "JSON (*.json)")
        if file:
            cfg = {
                "modbus": self.modbus_handler.serialize(),
                "mqtt"  : self.mqtt_handler.serialize(),
                "opcua" : self.opcua_handler.serialize(),
                "scanner": self.scanner_handler.serialize(),
                "s7": self.s7_handler.serialize(),
                "s7_tag": self.s7_tag_handler.serialize()
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
            self.scanner_handler.deserialize(cfg.get("scanner", {}))
            self.s7_handler.deserialize(cfg.get("s7", {}))
            self.s7_tag_handler.deserialize(cfg.get("s7_tag", {}))
            QMessageBox.information(self, "Bilgi", "Ayarlar yüklendi.")

    def update_opcua_tree_view(self, model):
        """OPC-UA TreeView'i gelen model ile günceller."""
        self.opcuaTreeView.setModel(model)
        self.opcuaTreeView.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.opcuaTreeView.expandToDepth(0) # Sadece ilk seviyeyi açık göster

    # ---------- OPC-UA Fonksiyonları ----------
    def connect_opcua(self):
        """OPC-UA bağlantı butonuna basıldığında çalışır."""
        endpoint = self.opcuaEndpointEdit.text()
        user = self.opcuaUserEdit.text()
        password = self.opcuaPassEdit.text()
        policy = self.opcuaSecurityPolicyCombo.currentText()
        mode = self.opcuaSecurityModeCombo.currentText()
        cert_path = self.opcuaCertEdit.text()
        key_path = self.opcuaKeyEdit.text()

        # Eğer güvenlik politikası "None" ise, diğer güvenlik ayarlarını temizle
        if policy == "None":
            mode = "None"
            cert_path = ""
            key_path = ""

        self.opcua_handler.connect(endpoint, user, password, policy, mode, cert_path, key_path)

    def browse_opcua_cert(self):
        """Sertifika dosyası seçmek için dosya diyalogunu açar."""
        file, _ = QFileDialog.getOpenFileName(self, "Sertifika Dosyası Seç", "", "Sertifika Dosyaları (*.der *.pem);;Tüm Dosyalar (*.*)")
        if file:
            self.opcuaCertEdit.setText(file)

    def browse_opcua_key(self):
        """Özel anahtar dosyası seçmek için dosya diyalogunu açar."""
        file, _ = QFileDialog.getOpenFileName(self, "Özel Anahtar Dosyası Seç", "", "Anahtar Dosyaları (*.pem);;Tüm Dosyalar (*.*)")
        if file:
            self.opcuaKeyEdit.setText(file)

    def on_opcua_node_double_clicked(self, index):
        """Ağaçtaki bir node'a çift tıklandığında çalışır."""
        item = self.opcuaTreeView.model().itemFromIndex(index)
        node_id = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if not node_id:
            return

        self.append_log(f"Node seçildi: {node_id}. Değer okunuyor ve abone olunuyor...")

        # Önceki plot verilerini ve aboneliği temizle
        self.opcua_plot_data_x.clear()
        self.opcua_plot_data_y.clear()
        self.opcua_plot_line.setData(self.opcua_plot_data_x, self.opcua_plot_data_y)
        self.opcuaValueEdit.clear()
        self.opcua_subscribed_node_id = node_id

        # Anlık değeri oku ve sürekli güncelleme için abone ol
        self.opcua_handler.read_node_value(node_id)
        self.opcua_handler.subscribe_to_node(node_id)

    def update_opcua_node_value(self, node_id, value):
        """OPC-UA'dan gelen yeni değeri arayüzde günceller."""
        if node_id != self.opcua_subscribed_node_id:
            return

        self.opcuaValueEdit.setText(f"{value}")

        if isinstance(value, (int, float)):
            self.opcua_plot_data_y.append(value)
            self.opcua_plot_data_x.append(len(self.opcua_plot_data_x))

            if len(self.opcua_plot_data_x) > 100: # Grafikte en fazla 100 nokta tut
                self.opcua_plot_data_x.pop(0)
                self.opcua_plot_data_y.pop(0)

            self.opcua_plot_line.setData(self.opcua_plot_data_x, self.opcua_plot_data_y)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
