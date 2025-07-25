# /protocols/opc_ua_handler.py
import asyncio
import threading
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import QAbstractItemView
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from asyncua import Client, ua
from protocols.base_handler import ProtocolHandlerBase


class OpcUaWorker(QThread):
    tree_ready    = pyqtSignal(object)      # dinamik ağaç
    value_changed = pyqtSignal(float)       # grafik için
    connected     = pyqtSignal(bool)

    def __init__(self, url, user, pwd):
        super().__init__()
        self.url, self.user, self.pwd = url, user, pwd
        self.loop = asyncio.new_event_loop()
        self.client = None
        self.graph_sub, self.graph_sub_handle = None, None
        self.selected_node = None

    def run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._run())

    async def _run(self):
        try:
            self.client = Client(self.url)
            if self.user:
                self.client.set_user(self.user)
                self.client.set_password(self.pwd)
            await self.client.connect()
            self.connected.emit(True)

            # 1) Dinamik ağaç
            model = QStandardItemModel()
            model.setHorizontalHeaderLabels(["Node"])
            await self._build_tree(model, self.client.nodes.objects)
            self.tree_ready.emit(model)

            # 3) Döngü
            while True:
                await asyncio.sleep(1)

        except Exception as e:
            print("[OPC-UA-WORKER] Error:", e)
            self.connected.emit(False)

    async def _build_tree(self, model, root_node, parent_item=None):
        if parent_item is None:
            parent_item = model.invisibleRootItem()
        try:
            children = await root_node.get_children()
            for ch in children:
                name = await ch.read_browse_name()
                item = QStandardItem(str(name.Name))
                item.setData(ch, Qt.ItemDataRole.UserRole)
                parent_item.appendRow(item)
                await self._build_tree(model, ch, item)
        except Exception:
            pass

    async def subscribe_to_node_for_graph(self, node_to_subscribe):
        try:
            if await node_to_subscribe.read_node_class() != ua.NodeClass.Variable:
                print(f"[OPC-UA-WORKER] Node {node_to_subscribe} bir değişken değil. Abone olunamaz.")
                return
        except Exception as e:
            print(f"[OPC-UA-WORKER] Node sınıfı okunamadı: {e}")
            return

        if self.graph_sub and self.graph_sub_handle:
            try:
                await self.graph_sub.unsubscribe(self.graph_sub_handle)
            except Exception as e:
                print(f"[OPC-UA-WORKER] Abonelik iptal hatası: {e}")
            self.graph_sub_handle = None

        if self.graph_sub is None:
            self.graph_sub = await self.client.create_subscription(500, self)

        self.graph_sub_handle = await self.graph_sub.subscribe_data_change(node_to_subscribe)
        print(f"[OPC-UA-WORKER] Grafik için abone olundu: {node_to_subscribe}")

    def datachange_notification(self, node, val, data):
        # grafik için sadece ilk sayısal Variable’ı kullanabilirsiniz
        try:
            self.value_changed.emit(float(val))
        except Exception:
            pass

    async def _stop_async(self):
        if self.graph_sub:
            await self.graph_sub.delete()
        if self.client:
            await self.client.disconnect()

    def stop(self):
        if self.client:
            asyncio.run_coroutine_threadsafe(self._stop_async(), self.loop)


class OpcUaHandler(ProtocolHandlerBase):
    def __init__(self, ui):
        super().__init__(ui)
        self.worker = None
        self.is_graphing = False
        self.data = []
        self._connect_signals()

    def _connect_signals(self):
        # Çift tıklama ile düzenleme moduna geçmesini engelle
        self.ui.opcuaTreeView.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.ui.opcuaTreeView.doubleClicked.connect(self.graph_node_selected)
        self.ui.opcuaConnectBtn.clicked.connect(self.toggle_connection)
        self.ui.opcuaTreeView.clicked.connect(self.node_selected)
        self.ui.opcuaWriteBtn.clicked.connect(self.write_value)

    def toggle_connection(self):
        if self.worker and self.worker.isRunning():
            self.disconnect()
        else:
            self.connect()

    def connect(self):
        url  = self.ui.opcuaEndpointEdit.text()
        user = self.ui.opcuaUserEdit.text()
        pwd  = self.ui.opcuaPassEdit.text()
        self.worker = OpcUaWorker(url, user, pwd)
        self.worker.tree_ready.connect(self.ui.opcuaTreeView.setModel)
        self.worker.value_changed.connect(self.update_value)
        self.worker.connected.connect(lambda ok: self.log_message.emit("OPC-UA bağlandı." if ok else "OPC-UA hatası."))
        self.is_graphing = False
        self.worker.start()

    def disconnect(self):
        if self.worker:
            self.worker.stop()
            self.worker.quit()
            self.worker.wait()
            self.worker = None
        self.is_graphing = False
        self.data.clear()
        plot_widget = getattr(self.ui, 'opcuaPlot', None)
        if plot_widget:
            plot_widget.clear()
        self.log_message.emit("OPC-UA bağlantısı kesildi.")

    def node_selected(self, index):
        if not index.isValid() or not self.worker:
            return
        node = index.data(Qt.ItemDataRole.UserRole)
        self.worker.selected_node = node

        if node:
            try:
                val = asyncio.run_coroutine_threadsafe(
                    node.read_value(), self.worker.loop
                ).result()
                self.ui.opcuaValueEdit.setText(str(val))
                self.log_message.emit(f"Seçili node değeri: {val}")
            except Exception as e:
                self.log_message.emit(f"Node okuma hatası: {e}")

    def graph_node_selected(self, index):
        if not index.isValid() or not self.worker or not self.worker.isRunning():
            return

        node = index.data(Qt.ItemDataRole.UserRole)
        if node:
            self.is_graphing = True
            self.data.clear()
            plot_widget = getattr(self.ui, 'opcuaPlot', None)
            if plot_widget:
                plot_widget.clear()
            self.log_message.emit(f"Grafik için node seçildi: {node}")

            asyncio.run_coroutine_threadsafe(
                self.worker.subscribe_to_node_for_graph(node), self.worker.loop
            )

    def update_value(self, val):
        if not self.is_graphing:
            return

        self.log_message.emit(f"[GUI] Yeni değer geldi: {val}")
        
        # Abone olunan node'un son değerini "Node Value" kutusunda da göster
        self.ui.opcuaValueEdit.setText(str(val))

        # Grafik güncelleme
        self.data.append(val)
        if len(self.data) > 100:
            self.data.pop(0)
        plot_widget = getattr(self.ui, 'opcuaPlot', None)
        if plot_widget:
            plot_widget.plot(list(range(len(self.data))), self.data, clear=True)

    def write_value(self):
        val_str = self.ui.opcuaWriteEdit.text()
        node = self.worker.selected_node if hasattr(self.worker, 'selected_node') else None
        if not val_str or not self.worker or not node:
            return
        try:
            val = float(val_str)
            asyncio.run_coroutine_threadsafe(
                node.write_value(ua.Variant(val, ua.VariantType.Double)),
                self.worker.loop
            )
            self.log_message.emit(f"OPC-UA yazıldı: {val}")
        except ValueError:
            self.log_message.emit("Geçerli sayı girin!")

    def get_status(self) -> str:
        return "connected" if self.worker and self.worker.isRunning() else "disconnected"

    def serialize(self) -> dict:
        return {
            "endpoint": self.ui.opcuaEndpointEdit.text(),
            "user": self.ui.opcuaUserEdit.text(),
            "pass": self.ui.opcuaPassEdit.text()
        }

    def deserialize(self, data: dict):
        self.ui.opcuaEndpointEdit.setText(data.get("endpoint", "opc.tcp://127.0.0.1:4840"))
        self.ui.opcuaUserEdit.setText(data.get("user", ""))
        self.ui.opcuaPassEdit.setText(data.get("pass", ""))