import socket
from PyQt6.QtCore import QThread, pyqtSignal, QObject
from PyQt6.QtWidgets import QTableWidgetItem
import ipaddress
import platform
import subprocess


class ScannerWorker(QThread):
    scan_result = pyqtSignal(str, int, str, str)  # ip, port, protocol, status
    scan_progress = pyqtSignal(int)  # progress percentage
    scan_finished = pyqtSignal()

    def __init__(self, network):
        super().__init__()
        self.network = network
        self.running = True
        # Common IIoT ports to scan
        self.ports_to_scan = [
            (502, "Modbus"),
            (1883, "MQTT"),
            (8883, "MQTT SSL"),
            (4840, "OPC UA"),
            (5000, "OPC UA"),
            (443, "HTTPS"),
            (80, "HTTP")
        ]
    def _is_host_alive(self, ip):
            """
            Sends a single ping to the given IP address to check if it's online.
            Returns True if alive, False otherwise.
            """
            try:
                # İşletim sistemine göre ping komutunu ayarla
                param = '-n' if platform.system().lower() == 'windows' else '-c'
                command = ['ping', param, '1', '-w', '1', ip] # -w 1 (1 saniye timeout)
    
                # Komutu çalıştır ve çıktısını gizle
                result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                # Ping başarılı ise return code 0 olur
                return result.returncode == 0
            except Exception:
                return False
    
    def run(self):
        try:
            # Parse network
            network = ipaddress.ip_network(self.network, strict=False)
            total_hosts = network.num_addresses
            scanned = 0

            # Scan each IP in the network
            for ip in network.hosts():
                if not self.running:
                    break

                ip_str = str(ip)

                # YENİ EKLENEN KONTROL
                # Portları taramadan önce host'un aktif olup olmadığını kontrol et
                if self._is_host_alive(ip_str):
                    # Scan ports for this IP
                    for port, protocol in self.ports_to_scan:
                        if not self.running:
                            break
                        
                        status = self._check_port(ip_str, port)
                        if status == "Open":
                            self.scan_result.emit(ip_str, port, protocol, status)
                
                # İlerleme çubuğu, host ping'e cevap vermese bile güncellenmeli
                scanned += 1
                progress = int((scanned / total_hosts) * 100)
                self.scan_progress.emit(progress)

            self.scan_finished.emit()
        except Exception as e:
            print(f"Scanner error: {e}")
            self.scan_finished.emit()

    def _check_port(self, ip, port, timeout=1):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            return "Open" if result == 0 else "Closed"
        except:
            return "Error"

    def stop(self):
        self.running = False


class ScannerHandler(QObject):
    log_message = pyqtSignal(str)
    
    def __init__(self, ui):
        super().__init__()
        self.ui = ui
        self.worker = None
        self._connect_signals()
        self._setup_table()

    def _connect_signals(self):
        self.ui.scannerScanBtn.clicked.connect(self.start_scan)
        self.ui.scannerStopBtn.clicked.connect(self.stop_scan)

    def _setup_table(self):
        """Sets up the table for displaying scan results."""
        tw = self.ui.scannerTable
        tw.setColumnCount(4)
        tw.setHorizontalHeaderLabels(["IP Address", "Port", "Protocol", "Status"])
        tw.setRowCount(0)  # Start with empty table

    def start_scan(self):
        """Starts the network scanning process."""
        network = self.ui.scannerNetworkEdit.text()
        if not network:
            self.log_message.emit("Please enter a valid network range.")
            return

        # Clear previous results
        self.ui.scannerTable.setRowCount(0)
        
        # Start scanning
        self.worker = ScannerWorker(network)
        self.worker.scan_result.connect(self.add_scan_result)
        self.worker.scan_progress.connect(self.ui.scannerProgressBar.setValue)
        self.worker.scan_finished.connect(self.scan_finished)
        self.worker.start()
        
        # Update UI
        self.ui.scannerScanBtn.setEnabled(False)
        self.ui.scannerStopBtn.setEnabled(True)
        self.log_message.emit(f"Started scanning network: {network}")

    def stop_scan(self):
        """Stops the network scanning process."""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
            self.scan_finished()
            self.log_message.emit("Scan stopped by user.")

    def add_scan_result(self, ip, port, protocol, status):
        """Adds a scan result to the table."""
        tw = self.ui.scannerTable
        row = tw.rowCount()
        tw.insertRow(row)
        
        tw.setItem(row, 0, QTableWidgetItem(ip))
        tw.setItem(row, 1, QTableWidgetItem(str(port)))
        tw.setItem(row, 2, QTableWidgetItem(protocol))
        tw.setItem(row, 3, QTableWidgetItem(status))
        
        # Auto-scroll to bottom
        tw.scrollToBottom()

    def scan_finished(self):
        """Called when scanning is finished."""
        self.ui.scannerScanBtn.setEnabled(True)
        self.ui.scannerStopBtn.setEnabled(False)
        self.ui.scannerProgressBar.setValue(100)
        self.log_message.emit("Network scan completed.")

    def get_status(self) -> str:
        return "scanning" if self.worker and self.worker.isRunning() else "idle"

    def serialize(self) -> dict:
        return {
            "network": self.ui.scannerNetworkEdit.text()
        }

    def deserialize(self, data: dict):
        self.ui.scannerNetworkEdit.setText(data.get("network", "192.168.1.0/24"))
