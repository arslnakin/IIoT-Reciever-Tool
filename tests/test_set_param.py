import snap7
import ctypes
import traceback

client = snap7.client.Client()
try:
    print("Attempting to set param with int...")
    client.set_param(2, 102)
    print("Success with int")
except Exception:
    traceback.print_exc()

try:
    print("Attempting to set param with ctypes...")
    value = ctypes.c_int(102)
    client.set_param(2, ctypes.byref(value))
    print("Success with ctypes.byref")
except Exception:
    traceback.print_exc()

try:
    print("Attempting to set param with ctypes value...")
    value = ctypes.c_int(102)
    client.set_param(2, value)
    print("Success with ctypes value")
except Exception:
    traceback.print_exc()
