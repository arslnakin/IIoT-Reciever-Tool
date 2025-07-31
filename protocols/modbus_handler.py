from PyQt6.QtCore import QThread, pyqtSignal
from pymodbus.client import ModbusTcpClient, ModbusSerialClient
from PyQt6.QtWidgets import QTableWidgetItem
from protocols.base_handler import ProtocolHandlerBase
import time

class ModbusWorker(QThread):
    data_ready = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, client, params):
        super().__init__()
        self.client = client
        self.params = params
        self.running = False

    def run(self):
        self.running = True
        while self.running:
            try:
                if self.params["func"] == 3:  # Holding registers
                    rr = self.client.read_holding_registers(
                        self.params["address"],
                        self.params["count"],
                        slave=self.params["slave"]
                    )
                elif self.params["func"] == 1:  # Coils
                    rr = self.client.read_coils(
                        self.params["address"],
                        self.params["count"],
                        slave=self.params["slave"]
                    )
                if rr.isError():
                    self.error_occurred.emit(str(rr))
                else:
                    self.data_ready.emit(rr.registers if hasattr(rr, 'registers') else rr.bits)
            except Exception as e:
                self.error_occurred.emit(str(e))
            time.sleep(self.params["interval"] / 1000)

    def stop(self):
        self.running = False

class ModbusHandler(ProtocolHandlerBase):
    def __init__(self, ui):
        super().__init__(ui)
        self.client = None
        self.worker = None
        self.polling_params = None
        self._connect_signals()
        self._setup_table()

    def _connect_signals(self):
        self.ui.modbusConnectBtn.clicked.connect(self.toggle_connection)
        self.ui.modbusPollChk.toggled.connect(self.toggle_polling)

    def _setup_table(self):
        """Modbus tablosunu adres sütunuyla birlikte yeniden yapılandırır."""
        tw = self.ui.modbusTable
        tw.setColumnCount(4)
        tw.setHorizontalHeaderLabels(["Adres", "Değer (Dec)", "Değer (Hex)", "Değer (Bin)"])
        tw.resizeColumnsToContents()

    def toggle_connection(self):
        if self.client and self.client.is_socket_open():
            self.disconnect()
        else:
            self.connect()

    def connect(self):
        ctype = self.ui.modbusConnType.currentText()
        try:
            if ctype == "TCP":
                self.client = ModbusTcpClient(
                    host=self.ui.modbusIpEdit.text(),
                    port=int(self.ui.modbusPortEdit.text())
                )
            else:  # RTU
                self.client = ModbusSerialClient(
                    port=self.ui.modbusComCombo.currentText(),
                    baudrate=int(self.ui.modbusBaudCombo.currentText())
                )
            if self.client.connect():
                self.log_message.emit("Modbus bağlantısı kuruldu.")
                self.ui.modbusConnectBtn.setText("Bağlantıyı Kes")
            else:
                self.log_message.emit("Modbus bağlantısı kurulamadı.")
        except Exception as e:
            self.log_message.emit(f"Modbus hata: {e}")

    def disconnect(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
            self.worker = None
            self.polling_params = None
        if self.client:
            self.client.close()
            self.client = None
        self.ui.modbusConnectBtn.setText("Bağlan")
        self.log_message.emit("Modbus bağlantısı kesildi.")

    def toggle_polling(self, checked):
        if checked and self.client and self.client.is_socket_open():
            self.polling_params = {
                "func": int(self.ui.modbusFuncCombo.currentText()),
                "address": int(self.ui.modbusAddrEdit.text()),
                "count": int(self.ui.modbusCountEdit.text()),
                "slave": int(self.ui.modbusSlaveEdit.text()),
                "interval": self.ui.modbusPollMsSpin.value()
            }
            self.worker = ModbusWorker(self.client, self.polling_params)
            self.worker.data_ready.connect(self.fill_table)
            self.worker.error_occurred.connect(lambda x: self.log_message.emit(f"Modbus Hata: {x}"))
            self.worker.start()
        else:
            if self.worker:
                self.worker.stop()
                self.worker.wait()
                self.worker = None
            self.polling_params = None

    def fill_table(self, data):
        if not self.polling_params:
            return

        tw = self.ui.modbusTable
        start_addr = self.polling_params["address"]
        func_code = self.polling_params["func"]

        # Modbus adresleme kuralına göre offset belirle
        addr_offset = 0
        if func_code == 1:    # Coils
            addr_offset = 1
        elif func_code == 3:  # Holding Registers
            addr_offset = 40001
        elif func_code == 4:  # Input Registers
            addr_offset = 30001
        elif func_code == 2:  # Discrete Inputs
            addr_offset = 10001

        tw.setRowCount(len(data))
        for row, val in enumerate(data):
            display_addr = addr_offset + start_addr + row
            tw.setItem(row, 0, self._mk_item(str(display_addr)))
            tw.setItem(row, 1, self._mk_item(str(val)))
            tw.setItem(row, 2, self._mk_item(hex(val)))
            tw.setItem(row, 3, self._mk_item(bin(val)))

    def _mk_item(self, text):
        return QTableWidgetItem(text)

    def get_status(self) -> str:
        return "connected" if self.client and self.client.is_socket_open() else "disconnected"

    def serialize(self) -> dict:
        return {
            "ip": self.ui.modbusIpEdit.text(),
            "port": self.ui.modbusPortEdit.text(),
            "com": self.ui.modbusComCombo.currentText(),
            "baud": self.ui.modbusBaudCombo.currentText(),
            "func": self.ui.modbusFuncCombo.currentText(),
            "addr": self.ui.modbusAddrEdit.text(),
            "count": self.ui.modbusCountEdit.text(),
            "slave": self.ui.modbusSlaveEdit.text(),
            "poll": self.ui.modbusPollChk.isChecked(),
            "poll_ms": self.ui.modbusPollMsSpin.value()
        }

    def deserialize(self, data: dict):
        self.ui.modbusIpEdit.setText(data.get("ip", "127.0.0.1"))
        self.ui.modbusPortEdit.setText(data.get("port", "502"))
        idx = self.ui.modbusComCombo.findText(data.get("com", "COM1"))
        if idx != -1:
            self.ui.modbusComCombo.setCurrentIndex(idx)
        idx = self.ui.modbusBaudCombo.findText(data.get("baud", "9600"))
        if idx != -1:
            self.ui.modbusBaudCombo.setCurrentIndex(idx)
        idx = self.ui.modbusFuncCombo.findText(data.get("func", "3"))
        if idx != -1:
            self.ui.modbusFuncCombo.setCurrentIndex(idx)
        self.ui.modbusAddrEdit.setText(data.get("addr", "0"))
        self.ui.modbusCountEdit.setText(data.get("count", "10"))
        self.ui.modbusSlaveEdit.setText(data.get("slave", "1"))
        self.ui.modbusPollChk.setChecked(data.get("poll", False))
        self.ui.modbusPollMsSpin.setValue(data.get("poll_ms", 1000))