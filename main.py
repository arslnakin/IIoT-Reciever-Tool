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
from protocols.gateway_handler import GatewayHandler
from protocols.dashboard_handler import DashboardHandler
from utils.logger import DataLogger

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

        # Logger
        self.data_logger = DataLogger()
        self.data_logger.log_message.connect(self.append_log)

        # Protokol handler'ları
        self.modbus_handler = ModbusHandler(self)
        self.mqtt_handler   = MqttHandler(self)
        self.opcua_handler  = OpcUaHandler(self)
        self.scanner_handler = ScannerHandler(self)
        self.s7_handler = S7Handler(self)
        self.s7_tag_handler = S7TagHandler(self)
        
        # Gateway Handler
        self.gateway_handler = GatewayHandler(self)
        self.gateway_handler.log_message.connect(self.append_log)

        # Dashboard Handler
        self.dashboard_handler = DashboardHandler(self)
        self.dashboard_handler.log_message.connect(self.append_log)

        # Connect Data Signals to Logger, Gateway, and Dashboard
        self.s7_tag_handler.data_received.connect(self.data_logger.log)
        self.s7_tag_handler.data_received.connect(self.gateway_handler.process_data)
        self.s7_tag_handler.data_received.connect(self.dashboard_handler.update_value)
        
        # Add other handlers here when they support data_received

        # OPC-UA Plotting
        self.opcua_plot_data_x = []
        self.opcua_plot_data_y = []
        self.opcua_plot_line = self.opcuaPlot.plot(pen='y')
        self.opcua_subscribed_node_id = None

        # Menü aksiyonları
        self.actionSave.triggered.connect(self.save_config)
        self.actionLoad.triggered.connect(self.load_config)
        
        # Logging Menu
        self.menuLogging = self.menubar.addMenu("Logging")
        self.actionStartLogging = self.menuLogging.addAction("Start Logging")
        self.actionStopLogging = self.menuLogging.addAction("Stop Logging")
        
        self.actionStartLogging.triggered.connect(self.start_logging)
        self.actionStopLogging.triggered.connect(self.stop_logging)

        # View Menu (Dark Mode)
        self.menuView = self.menubar.addMenu("View")
        self.actionToggleDarkMode = self.menuView.addAction("Toggle Dark Mode")
        self.actionToggleDarkMode.setCheckable(True)
        self.actionToggleDarkMode.triggered.connect(self.toggle_dark_mode)

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

    def start_logging(self):
        file, _ = QFileDialog.getSaveFileName(self, "Save Log File", "", "CSV Files (*.csv)")
        if file:
            self.data_logger.start(file)

    def stop_logging(self):
        self.data_logger.stop()

    def toggle_dark_mode(self, checked):
        app = QApplication.instance()
        if checked:
            # Dark Mode Palette
            from PyQt6.QtGui import QPalette, QColor
            palette = QPalette()
            palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
            palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
            palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
            palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
            palette.setColor(QPalette.ColorRole.ToolTipText, QColor(255, 255, 255))
            palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
            palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
            palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
            palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
            palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))
            app.setPalette(palette)
            app.setStyle("Fusion")
        else:
            # Restore Default
            app.setPalette(QApplication.style().standardPalette())
            app.setStyle("Windows")

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
                "s7_tag": self.s7_tag_handler.serialize(),
                "gateway": self.gateway_handler.serialize(),
                "dashboard": self.dashboard_handler.serialize()
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
            self.gateway_handler.deserialize(cfg.get("gateway", {}))
            self.dashboard_handler.deserialize(cfg.get("dashboard", {}))
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
