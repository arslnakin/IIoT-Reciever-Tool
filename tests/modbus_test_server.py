import time, random, threading
from pymodbus.server import StartTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext

context_holder = None        # global context'e referans

def updating_writer():
    """Arka planda verileri günceller."""
    global context_holder
    while True:
        time.sleep(3)
        if context_holder is None:
            continue

        slave = context_holder[0]

        # 1) Holding register 0-4  -> +1
        hr = slave.getValues(3, 0, count=5)
        hr = [(v + 1) % 65536 for v in hr]
        slave.setValues(3, 0, hr)

        # 2) Coil 0-4 -> toggle
        co = slave.getValues(1, 0, count=5)
        co = [not v for v in co]
        slave.setValues(1, 0, co)

        # 3) Input register 0-4 -> random
        ir = [random.randint(0, 99) for _ in range(5)]
        slave.setValues(4, 0, ir)

        print(f"[LIVE] HR0-4={hr}  CO0-4={co}  IR0-4={ir}")

def run_modbus_server():
    global context_holder
    store = ModbusSlaveContext(
        di=ModbusSequentialDataBlock(0, [10] * 100),
        co=ModbusSequentialDataBlock(0, [False] * 100),
        hr=ModbusSequentialDataBlock(0, [30] * 100),
        ir=ModbusSequentialDataBlock(0, [40] * 100)
    )
    context = ModbusServerContext(slaves=store, single=True)
    context_holder = context

    address = ("127.0.0.4", 502)
    print(f"Modbus TCP live server {address} starting...")
    # Güncelleyici thread'i başlat
    threading.Thread(target=updating_writer, daemon=True).start()
    StartTcpServer(context=context, address=address)

if __name__ == "__main__":
    run_modbus_server()