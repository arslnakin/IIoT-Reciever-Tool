from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QHeaderView, QComboBox, QLabel, QLineEdit

class GatewayHandler(QObject):
    log_message = pyqtSignal(str)

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.rules = [] # List of dicts
        self.active = False
        
        # UI Setup
        self.setup_ui()

    def setup_ui(self):
        self.tab = QWidget()
        layout = QVBoxLayout(self.tab)
        
        # Controls
        ctrl_layout = QHBoxLayout()
        self.btn_add = QPushButton("Add Rule")
        self.btn_remove = QPushButton("Remove Rule")
        self.btn_start = QPushButton("Start Gateway")
        self.btn_start.setCheckable(True)
        
        ctrl_layout.addWidget(self.btn_add)
        ctrl_layout.addWidget(self.btn_remove)
        ctrl_layout.addWidget(self.btn_start)
        ctrl_layout.addStretch()
        
        layout.addLayout(ctrl_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "If Protocol", "If Tag", "Operator", "Value", 
            "Then Protocol", "Then Tag", "Value"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        
        # Add tab to main window
        self.main_window.tabWidget.addTab(self.tab, "Gateway")
        
        # Connections
        self.btn_add.clicked.connect(self.add_rule_row)
        self.btn_remove.clicked.connect(self.remove_rule_row)
        self.btn_start.toggled.connect(self.toggle_gateway)

    def add_rule_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # If Protocol
        cb_if_proto = QComboBox()
        cb_if_proto.addItems(["S7", "Modbus", "MQTT", "OPC-UA"])
        self.table.setCellWidget(row, 0, cb_if_proto)
        
        # If Tag
        self.table.setItem(row, 1, QTableWidgetItem(""))
        
        # Operator
        cb_op = QComboBox()
        cb_op.addItems([">", "<", "==", "!=", ">=", "<="])
        self.table.setCellWidget(row, 2, cb_op)
        
        # Value
        self.table.setItem(row, 3, QTableWidgetItem("0"))
        
        # Then Protocol
        cb_then_proto = QComboBox()
        cb_then_proto.addItems(["S7", "Modbus", "MQTT", "OPC-UA"])
        self.table.setCellWidget(row, 4, cb_then_proto)
        
        # Then Tag
        self.table.setItem(row, 5, QTableWidgetItem(""))
        
        # Then Value
        self.table.setItem(row, 6, QTableWidgetItem("1"))

    def remove_rule_row(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    def toggle_gateway(self, checked):
        self.active = checked
        if checked:
            self.btn_start.setText("Stop Gateway")
            self.parse_rules()
            self.log_message.emit("Gateway Started")
        else:
            self.btn_start.setText("Start Gateway")
            self.log_message.emit("Gateway Stopped")

    def parse_rules(self):
        self.rules = []
        for row in range(self.table.rowCount()):
            try:
                rule = {
                    "if_proto": self.table.cellWidget(row, 0).currentText(),
                    "if_tag": self.table.item(row, 1).text(),
                    "op": self.table.cellWidget(row, 2).currentText(),
                    "if_val": self.table.item(row, 3).text(),
                    "then_proto": self.table.cellWidget(row, 4).currentText(),
                    "then_tag": self.table.item(row, 5).text(),
                    "then_val": self.table.item(row, 6).text()
                }
                self.rules.append(rule)
            except Exception:
                pass

    def process_data(self, protocol, tag, value):
        if not self.active:
            return
            
        for rule in self.rules:
            if rule["if_proto"] == protocol and rule["if_tag"] == tag:
                if self.check_condition(value, rule["op"], rule["if_val"]):
                    self.execute_action(rule["then_proto"], rule["then_tag"], rule["then_val"])

    def check_condition(self, val1, op, val2):
        try:
            v1 = float(val1)
            v2 = float(val2)
            if op == ">": return v1 > v2
            if op == "<": return v1 < v2
            if op == "==": return v1 == v2
            if op == "!=": return v1 != v2
            if op == ">=": return v1 >= v2
            if op == "<=": return v1 <= v2
        except:
            # String comparison
            v1 = str(val1)
            v2 = str(val2)
            if op == "==": return v1 == v2
            if op == "!=": return v1 != v2
        return False

    def execute_action(self, protocol, tag, value):
        self.log_message.emit(f"Gateway Trigger: {protocol} {tag} = {value}")
        # Implementation for other protocols needed
        # For now, only S7 Tag Write is implemented in S7TagHandler
        
        if protocol == "S7":
            # Find S7 Tag Handler and write
            # This is tricky because S7TagHandler.write_tag takes a ROW index
            # We need a generic write method in handlers
            pass
        elif protocol == "MQTT":
            if hasattr(self.main_window, 'mqtt_handler'):
                self.main_window.mqtt_handler.publish(tag, value)

    def serialize(self):
        rules_data = []
        for row in range(self.table.rowCount()):
            rule = {
                "if_proto": self.table.cellWidget(row, 0).currentText(),
                "if_tag": self.table.item(row, 1).text() if self.table.item(row, 1) else "",
                "op": self.table.cellWidget(row, 2).currentText(),
                "if_val": self.table.item(row, 3).text() if self.table.item(row, 3) else "",
                "then_proto": self.table.cellWidget(row, 4).currentText(),
                "then_tag": self.table.item(row, 5).text() if self.table.item(row, 5) else "",
                "then_val": self.table.item(row, 6).text() if self.table.item(row, 6) else ""
            }
            rules_data.append(rule)
        return {"rules": rules_data}

    def deserialize(self, data):
        rules = data.get("rules", [])
        self.table.setRowCount(0)
        for r in rules:
            self.add_rule_row()
            row = self.table.rowCount() - 1
            
            self.table.cellWidget(row, 0).setCurrentText(r.get("if_proto", "S7"))
            self.table.setItem(row, 1, QTableWidgetItem(r.get("if_tag", "")))
            self.table.cellWidget(row, 2).setCurrentText(r.get("op", ">"))
            self.table.setItem(row, 3, QTableWidgetItem(r.get("if_val", "0")))
            self.table.cellWidget(row, 4).setCurrentText(r.get("then_proto", "S7"))
            self.table.setItem(row, 5, QTableWidgetItem(r.get("then_tag", "")))
            self.table.setItem(row, 6, QTableWidgetItem(r.get("then_val", "1")))
