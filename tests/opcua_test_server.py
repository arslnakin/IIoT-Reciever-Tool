# opcua_live_server.py
import asyncio
import random
import threading
import time
from asyncua import Server, ua

ENDPOINT = "opc.tcp://127.0.0.2:4840"
NAMESPACE_URI = "http://test.local"

async def run_server():
    server = Server()
    await server.init()
    server.set_endpoint(ENDPOINT)
    server.set_security_policy([ua.SecurityPolicyType.NoSecurity])

    idx = await server.register_namespace(NAMESPACE_URI)
    root = server.nodes.objects
    obj = await root.add_object(idx, "TestObject")

    # Değişken tanımları
    var_float = await obj.add_variable(
        idx, "Temperature",
        ua.Variant(20.0, ua.VariantType.Double),
        datatype=ua.NodeId(ua.ObjectIds.Double)
    )
    var_uint = await obj.add_variable(
        idx, "Counter",
        ua.Variant(0, ua.VariantType.UInt32),
        datatype=ua.NodeId(ua.ObjectIds.UInt32)
    )
    var_bool = await obj.add_variable(
        idx, "Status",
        ua.Variant(False, ua.VariantType.Boolean),
        datatype=ua.NodeId(ua.ObjectIds.Boolean)
    )

    for v in (var_float, var_uint, var_bool):
        await v.set_writable()

    # terminal + node güncelleyici
    async def update_loop():
        cnt = 0
        while True:
            cnt += 1
            t = round(random.uniform(20.0, 30.0), 2)

            await var_float.write_value(ua.Variant(t, ua.VariantType.Double))
            await var_uint.write_value(ua.Variant(cnt, ua.VariantType.UInt32))
            await var_bool.write_value(ua.Variant(bool(cnt % 2), ua.VariantType.Boolean))

            # Konsola yaz
            print(f"[OPC-UA-LIVE] T={t}  C={cnt}  S={bool(cnt % 2)}")

            await asyncio.sleep(2)

    asyncio.create_task(update_loop())
    print("[OPC-UA-LIVE] Server started at", ENDPOINT)
    async with server:
        await asyncio.sleep(999999)

def aio_run():
    asyncio.run(run_server())

if __name__ == "__main__":
    threading.Thread(target=aio_run, daemon=True).start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping...")