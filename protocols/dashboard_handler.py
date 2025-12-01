from PyQt6.QtCore import QObject, pyqtSignal, Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel, QComboBox, QLineEdit, QDialog, QFormLayout, QFrame

class DashboardHandler(QObject):
    log_message = pyqtSignal(str)

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.widgets = [] # List of dicts {protocol, tag, label_widget, value_widget}
        
        self.setup_ui()

    def setup_ui(self):
        self.tab = QWidget()
        self.layout = QVBoxLayout(self.tab)
        
        # Controls
        ctrl_layout = QHBoxLayout()
        self.btn_add = QPushButton("Add Widget")
        self.btn_clear = QPushButton("Clear All")
        
        ctrl_layout.addWidget(self.btn_add)
        ctrl_layout.addWidget(self.btn_clear)
        ctrl_layout.addStretch()
        
        self.layout.addLayout(ctrl_layout)
        
        # Grid for widgets
        self.grid_frame = QFrame()
        self.grid_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.grid_layout = QGridLayout(self.grid_frame)
        self.layout.addWidget(self.grid_frame)
        self.layout.addStretch()
        
        # Add tab
        self.main_window.tabWidget.addTab(self.tab, "Dashboard")
        
        # Connections
        self.btn_add.clicked.connect(self.add_widget_dialog)
        self.btn_clear.clicked.connect(self.clear_widgets)

    def add_widget_dialog(self):
        dialog = QDialog(self.main_window)
        dialog.setWindowTitle("Add Dashboard Widget")
        layout = QFormLayout(dialog)
        
        cb_proto = QComboBox()
        cb_proto.addItems(["S7", "Modbus", "MQTT", "OPC-UA"])
        
        le_tag = QLineEdit()
        le_label = QLineEdit()
        le_label.setPlaceholderText("Display Name")
        
        btn_ok = QPushButton("Add")
        btn_ok.clicked.connect(dialog.accept)
        
        layout.addRow("Protocol:", cb_proto)
        layout.addRow("Tag/Topic:", le_tag)
        layout.addRow("Label:", le_label)
        layout.addRow(btn_ok)
        
        if dialog.exec():
            self.add_widget(
                cb_proto.currentText(),
                le_tag.text(),
                le_label.text()
            )

    def add_widget(self, protocol, tag, label_text):
        # Create UI elements
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        frame.setStyleSheet("background-color: #f0f0f0; border-radius: 5px; margin: 5px;")
        
        vbox = QVBoxLayout(frame)
        
        lbl_name = QLabel(label_text or tag)
        lbl_name.setStyleSheet("font-weight: bold; color: #333;")
        lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_value = QLabel("---")
        lbl_value.setStyleSheet("font-size: 24px; color: #0078d7;")
        lbl_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        vbox.addWidget(lbl_name)
        vbox.addWidget(lbl_value)
        
        # Add to grid
        count = len(self.widgets)
        row = count // 3
        col = count % 3
        self.grid_layout.addWidget(frame, row, col)
        
        # Store
        self.widgets.append({
            "protocol": protocol,
            "tag": tag,
            "label_text": label_text,
            "value_widget": lbl_value,
            "frame": frame
        })

    def clear_widgets(self):
        for w in self.widgets:
            w["frame"].setParent(None)
        self.widgets = []

    def update_value(self, protocol, tag, value):
        for w in self.widgets:
            if w["protocol"] == protocol and w["tag"] == tag:
                w["value_widget"].setText(str(value))

    def serialize(self):
        data = []
        for w in self.widgets:
            data.append({
                "protocol": w["protocol"],
                "tag": w["tag"],
                "label_text": w["label_text"]
            })
        return {"widgets": data}

    def deserialize(self, data):
        self.clear_widgets()
        widgets = data.get("widgets", [])
        for w in widgets:
            self.add_widget(w["protocol"], w["tag"], w["label_text"])
