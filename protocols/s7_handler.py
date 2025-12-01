import snap7
from snap7.util import *
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
from .base_handler import ProtocolHandlerBase

class S7Handler(ProtocolHandlerBase):
    def __init__(self, ui):
        super().__init__(ui)
        self.client = None
        self.connected = False
        self.timer = QTimer()
        self.timer.timeout.connect(self.read_data)
        self.ui.s7ConnectBtn.clicked.connect(self.toggle_connection)

        # Setup Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Offset (Dec)", "Offset (Hex)", "Value (Hex)", "Value (Dec)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # Replace s7DataOutput with table
        # Note: s7DataOutput is now in s7BlockLayout (child of s7BlockTab)
        # We need to find where it is.
        if hasattr(self.ui, 's7DataOutput'):
            parent = self.ui.s7DataOutput.parentWidget()
            if parent:
                layout = parent.layout()
                if layout:
                    index = layout.indexOf(self.ui.s7DataOutput)
                    if index != -1:
                        layout.removeWidget(self.ui.s7DataOutput)
                        self.ui.s7DataOutput.setParent(None)
                        layout.insertWidget(index, self.table)

    def ensure_client(self):
        if self.client is None:
            try:
                self.client = snap7.client.Client()
            except Exception as e:
                self.log_message.emit(f"Failed to load Snap7 library: {e}. Ensure snap7.dll is available.")
                return False
        return True

    def connect(self):
        if not self.ensure_client():
            return

        ip = self.ui.s7IpEdit.text()
        try:
            rack = int(self.ui.s7RackEdit.text())
            slot = int(self.ui.s7SlotEdit.text())
            port = int(self.ui.s7PortEdit.text())
        except ValueError:
            self.log_message.emit("S7 Error: Rack, Slot, and Port must be integers.")
            return

        try:
            # Set custom port if not 102
            if port != 102:
                import ctypes
                c_port = ctypes.c_int(port)
                self.client._lib.Cli_SetParam(self.client._s7_client, 2, ctypes.byref(c_port))
            
            self.client.connect(ip, rack, slot)
            self.connected = self.client.get_connected()
            if self.connected:
                self.log_message.emit(f"S7 Connected to {ip}:{port} (Rack={rack}, Slot={slot})")
                self.ui.s7ConnectBtn.setText("Disconnect")
                self.start_reading()
        except Exception as e:
            self.log_message.emit(f"S7 Connection Error: {e}")

    def disconnect(self):
        if self.connected:
            self.client.disconnect()
            self.connected = False
            self.stop_reading()
            self.ui.s7ConnectBtn.setText("Connect")
            self.log_message.emit("S7 Disconnected")

    def toggle_connection(self):
        if self.connected:
            self.disconnect()
        else:
            self.connect()

    def start_reading(self):
        try:
            interval = int(self.ui.s7IntervalEdit.text())
        except ValueError:
            interval = 1000
        self.timer.start(interval)

    def stop_reading(self):
        self.timer.stop()

    def read_data(self):
        if not self.connected:
            return
            
        try:
            db_number = int(self.ui.s7DbNumEdit.text())
            start = int(self.ui.s7StartEdit.text())
            size = int(self.ui.s7SizeEdit.text())
            
            # Read DB
            data = self.client.db_read(db_number, start, size)
            
            # Update Table
            self.table.setRowCount(len(data))
            for i, b in enumerate(data):
                offset_val = start + i
                # Offset (Dec)
                self.table.setItem(i, 0, QTableWidgetItem(f"{offset_val}.0"))
                # Offset (Hex)
                self.table.setItem(i, 1, QTableWidgetItem(f"{offset_val:X}.0"))
                # Value (Hex)
                self.table.setItem(i, 2, QTableWidgetItem(f"{b:02X}"))
                # Value (Dec)
                self.table.setItem(i, 3, QTableWidgetItem(str(b)))
            
        except Exception as e:
            self.log_message.emit(f"S7 Read Error: {e}")
            self.stop_reading()

    def get_status(self) -> str:
        return "Connected" if self.connected else "Disconnected"

    def serialize(self) -> dict:
        return {
            "ip": self.ui.s7IpEdit.text(),
            "rack": self.ui.s7RackEdit.text(),
            "slot": self.ui.s7SlotEdit.text(),
            "port": self.ui.s7PortEdit.text(),
            "db_num": self.ui.s7DbNumEdit.text(),
            "start": self.ui.s7StartEdit.text(),
            "size": self.ui.s7SizeEdit.text(),
            "interval": self.ui.s7IntervalEdit.text()
        }

    def deserialize(self, data: dict):
        self.ui.s7IpEdit.setText(data.get("ip", "192.168.0.1"))
        self.ui.s7RackEdit.setText(data.get("rack", "0"))
        self.ui.s7SlotEdit.setText(data.get("slot", "1"))
        self.ui.s7PortEdit.setText(data.get("port", "102"))
        self.ui.s7DbNumEdit.setText(data.get("db_num", "1"))
        self.ui.s7StartEdit.setText(data.get("start", "0"))
        self.ui.s7SizeEdit.setText(data.get("size", "10"))
        self.ui.s7IntervalEdit.setText(data.get("interval", "1000"))


class S7TagHandler(ProtocolHandlerBase):
    def __init__(self, ui):
        super().__init__(ui)
        self.client = None
        self.connected = False
        self.timer = QTimer()
        self.timer.timeout.connect(self.read_tags)
        
        # Connect UI signals
        self.ui.s7TagConnectBtn.clicked.connect(self.toggle_connection)
        self.ui.s7TagAddRowBtn.clicked.connect(self.add_row)
        self.ui.s7TagRemoveRowBtn.clicked.connect(self.remove_row)
        
        # Check if import button exists (it was added dynamically to UI file)
        if hasattr(self.ui, 's7TagImportBtn'):
            self.ui.s7TagImportBtn.clicked.connect(self.import_tags)
        
        # Setup Table
        self.table = self.ui.s7TagTable
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Offset", "Type", "Value", "Write Value", "Action", "Description"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def ensure_client(self):
        if self.client is None:
            try:
                self.client = snap7.client.Client()
            except Exception as e:
                self.log_message.emit(f"Failed to load Snap7 library: {e}")
                return False
        return True

    def connect(self):
        if not self.ensure_client():
            return

        ip = self.ui.s7TagIpEdit.text()
        try:
            rack = int(self.ui.s7TagRackEdit.text())
            slot = int(self.ui.s7TagSlotEdit.text())
            port = int(self.ui.s7TagPortEdit.text())
        except ValueError:
            self.log_message.emit("S7 Tag Error: Rack, Slot, and Port must be integers.")
            return

        try:
            if port != 102:
                import ctypes
                c_port = ctypes.c_int(port)
                self.client._lib.Cli_SetParam(self.client._s7_client, 2, ctypes.byref(c_port))
            
            self.client.connect(ip, rack, slot)
            self.connected = self.client.get_connected()
            if self.connected:
                self.log_message.emit(f"S7 Tag Monitor Connected to {ip}:{port}")
                self.ui.s7TagConnectBtn.setText("Disconnect")
                self.start_reading()
        except Exception as e:
            self.log_message.emit(f"S7 Tag Connection Error: {e}")

    def disconnect(self):
        if self.connected:
            self.client.disconnect()
            self.connected = False
            self.stop_reading()
            self.ui.s7TagConnectBtn.setText("Connect")
            self.log_message.emit("S7 Tag Monitor Disconnected")

    def toggle_connection(self):
        if self.connected:
            self.disconnect()
        else:
            self.connect()

    def start_reading(self):
        try:
            interval = int(self.ui.s7TagIntervalEdit.text())
        except ValueError:
            interval = 1000
        self.timer.start(interval)

    def stop_reading(self):
        self.timer.stop()

    def add_row(self):
        from PyQt6.QtWidgets import QComboBox, QPushButton, QLineEdit
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # Offset
        self.table.setItem(row, 0, QTableWidgetItem("0.0")) 
        
        # Type Combo
        combo = QComboBox()
        combo.addItems(["Bool", "Byte", "Int", "Word", "DInt", "DWord", "Real"])
        self.table.setCellWidget(row, 1, combo)
        
        # Value (Read-only)
        item_val = QTableWidgetItem("-")
        item_val.setFlags(item_val.flags() ^ QtCore.Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, 2, item_val)

        # Write Value (Editable)
        self.table.setItem(row, 3, QTableWidgetItem("0"))

        # Write Button
        btn = QPushButton("Write")
        btn.clicked.connect(lambda _, r=row: self.write_tag(r))
        self.table.setCellWidget(row, 4, btn)
        
        # Description
        self.table.setItem(row, 5, QTableWidgetItem(""))

    def remove_row(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    def import_tags(self):
        from PyQt6.QtWidgets import QFileDialog
        import csv
        
        file, _ = QFileDialog.getOpenFileName(self.ui, "Import Tags", "", "CSV Files (*.csv);;All Files (*.*)")
        if not file:
            return
            
        try:
            with open(file, newline='', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                # Optional: Skip header if present. Simple heuristic: check if first col is "Offset"
                rows = list(reader)
                if not rows:
                    return
                    
                if rows[0][0].lower() == "offset":
                    rows = rows[1:]
                
                for row_data in rows:
                    if len(row_data) < 2:
                        continue
                        
                    offset = row_data[0]
                    dtype = row_data[1]
                    desc = row_data[2] if len(row_data) > 2 else ""
                    
                    self.add_row()
                    row_idx = self.table.rowCount() - 1
                    
                    self.table.setItem(row_idx, 0, QTableWidgetItem(offset))
                    
                    combo = self.table.cellWidget(row_idx, 1)
                    if combo:
                        # Find closest match for type
                        index = combo.findText(dtype, QtCore.Qt.MatchFlag.MatchContains)
                        if index >= 0:
                            combo.setCurrentIndex(index)
                        else:
                            # Default or try to guess
                            pass
                            
                    self.table.setItem(row_idx, 5, QTableWidgetItem(desc))
                    
            self.log_message.emit(f"Imported {len(rows)} tags from {file}")
            
        except Exception as e:
            self.log_message.emit(f"Import Error: {e}")

    def write_tag(self, row):
        if not self.connected:
            self.log_message.emit("S7 Write Error: Not connected.")
            return

        try:
            db_number = int(self.ui.s7TagDbNumEdit.text())
        except ValueError:
            self.log_message.emit("S7 Write Error: Invalid DB Number.")
            return

        offset_item = self.table.item(row, 0)
        write_val_item = self.table.item(row, 3)
        combo = self.table.cellWidget(row, 1)

        if not offset_item or not write_val_item or not combo:
            return

        offset_str = offset_item.text()
        dtype = combo.currentText()
        write_val_str = write_val_item.text()

        import struct

        try:
            # Parse offset
            byte_offset = 0
            bit_offset = 0
            if '.' in offset_str:
                parts = offset_str.split('.')
                byte_offset = int(parts[0])
                if len(parts) > 1:
                    bit_offset = int(parts[1])
            else:
                byte_offset = int(offset_str)

            # Prepare data buffer
            data = bytearray()
            
            if dtype == "Bool":
                # For Bool, we need to read the byte first, modify the bit, and write back
                # Or use write_area? snap7 has set_bool but it works on a buffer.
                # Let's read 1 byte first to be safe and not overwrite other bits
                current_byte = self.client.db_read(db_number, byte_offset, 1)
                val_bool = (write_val_str.lower() in ['true', '1', 'on'])
                snap7.util.set_bool(current_byte, 0, bit_offset, val_bool)
                data = current_byte
            elif dtype == "Byte":
                val = int(write_val_str)
                data = bytearray([val])
            elif dtype == "Int":
                val = int(write_val_str)
                data = struct.pack('>h', val)
            elif dtype == "Word":
                val = int(write_val_str, 16) # Assume Hex input for Word
                data = struct.pack('>H', val)
            elif dtype == "DInt":
                val = int(write_val_str)
                data = struct.pack('>i', val)
            elif dtype == "DWord":
                val = int(write_val_str, 16) # Assume Hex input for DWord
                data = struct.pack('>I', val)
            elif dtype == "Real":
                val = float(write_val_str)
                data = struct.pack('>f', val)

            # Write to DB
            self.client.db_write(db_number, byte_offset, data)
            self.log_message.emit(f"S7 Write Success: Row {row+1} -> {write_val_str}")
            
        except Exception as e:
            self.log_message.emit(f"S7 Write Error: {e}")


    def read_tags(self):
        if not self.connected:
            return
            
        try:
            db_number = int(self.ui.s7TagDbNumEdit.text())
        except ValueError:
            return

        import struct

        for row in range(self.table.rowCount()):
            offset_item = self.table.item(row, 0)
            if not offset_item:
                continue
            
            offset_str = offset_item.text()
            
            # Get Type
            combo = self.table.cellWidget(row, 1)
            if not combo:
                continue
            dtype = combo.currentText()
            
            try:
                # Parse offset
                byte_offset = 0
                bit_offset = 0
                if '.' in offset_str:
                    parts = offset_str.split('.')
                    byte_offset = int(parts[0])
                    if len(parts) > 1:
                        bit_offset = int(parts[1])
                else:
                    byte_offset = int(offset_str)
                
                # Determine size and read
                size = 1
                if dtype in ["Bool", "Byte"]:
                    size = 1
                elif dtype in ["Int", "Word"]:
                    size = 2
                elif dtype in ["DInt", "DWord", "Real"]:
                    size = 4
                
                data = self.client.db_read(db_number, byte_offset, size)
                
                val_str = "Error"
                
                if dtype == "Bool":
                    # Get bit
                    val = snap7.util.get_bool(data, 0, bit_offset)
                    val_str = str(val)
                elif dtype == "Byte":
                    val = data[0]
                    val_str = str(val)
                elif dtype == "Int":
                    val = struct.unpack('>h', data)[0]
                    val_str = str(val)
                elif dtype == "Word":
                    val = struct.unpack('>H', data)[0]
                    val_str = f"{val:04X}" # Hex display for Word
                elif dtype == "DInt":
                    val = struct.unpack('>i', data)[0]
                    val_str = str(val)
                elif dtype == "DWord":
                    val = struct.unpack('>I', data)[0]
                    val_str = f"{val:08X}" # Hex display for DWord
                elif dtype == "Real":
                    val = struct.unpack('>f', data)[0]
                    val_str = f"{val:.4f}"
                
                self.table.setItem(row, 2, QTableWidgetItem(val_str))
                self.data_received.emit("S7", f"DB{db_number}.{offset_str}", val_str)
                
            except Exception as e:
                self.table.setItem(row, 2, QTableWidgetItem("Err"))
                # self.log_message.emit(f"Tag Read Error Row {row}: {e}")

    def get_status(self) -> str:
        return "Connected" if self.connected else "Disconnected"

    def serialize(self) -> dict:
        tags = []
        for row in range(self.table.rowCount()):
            off = self.table.item(row, 0).text() if self.table.item(row, 0) else ""
            
            combo = self.table.cellWidget(row, 1)
            dtype = combo.currentText() if combo else "Byte"
            
            desc = self.table.item(row, 5).text() if self.table.item(row, 5) else ""
            tags.append({"offset": off, "type": dtype, "desc": desc})
            
        return {
            "ip": self.ui.s7TagIpEdit.text(),
            "rack": self.ui.s7TagRackEdit.text(),
            "slot": self.ui.s7TagSlotEdit.text(),
            "port": self.ui.s7TagPortEdit.text(),
            "db_num": self.ui.s7TagDbNumEdit.text(),
            "interval": self.ui.s7TagIntervalEdit.text(),
            "tags": tags
        }

    def deserialize(self, data: dict):
        self.ui.s7TagIpEdit.setText(data.get("ip", "192.168.0.1"))
        self.ui.s7TagRackEdit.setText(data.get("rack", "0"))
        self.ui.s7TagSlotEdit.setText(data.get("slot", "1"))
        self.ui.s7TagPortEdit.setText(data.get("port", "102"))
        self.ui.s7TagDbNumEdit.setText(data.get("db_num", "1"))
        self.ui.s7TagIntervalEdit.setText(data.get("interval", "1000"))
        
        tags = data.get("tags", [])
        self.table.setRowCount(0)
        for t in tags:
            self.add_row()
            row = self.table.rowCount() - 1
            self.table.setItem(row, 0, QTableWidgetItem(t.get("offset", "0.0")))
            
            combo = self.table.cellWidget(row, 1)
            if combo:
                combo.setCurrentText(t.get("type", "Byte"))
                
            self.table.setItem(row, 5, QTableWidgetItem(t.get("desc", "")))
