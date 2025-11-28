import snap7
import snap7.server
import time
import struct
import sys
import ctypes

def run_server():
    print("Initializing S7 Server...")
    # We need to handle the memory properly
    server = snap7.server.Server()
    
    # Create a buffer
    db1_data = bytearray(100)
    # Convert to ctypes buffer for snap7
    c_data = (ctypes.c_ubyte * len(db1_data)).from_buffer(db1_data)
    
    # Register DB 1
    # srvAreaDB = 0x84
    server.register_area(snap7.SrvArea.DB, 1, c_data)
    
    # Define event callback
    def event_callback(event):
        print(f"Server Event: {event.EvtTime} - Code: {hex(event.EvtCode)} - Param1: {event.EvtParam1} - Param2: {event.EvtParam2}")
    
    # Set callback
    # We need to keep a reference to the callback to prevent garbage collection
    CALLBACK = ctypes.CFUNCTYPE(None, snap7.types.SrvEvent)
    c_callback = CALLBACK(event_callback)
    server.set_events_callback(c_callback)
    
    print("----------------------------------------------------------------")
    print("S7 Server Simulation")
    print("----------------------------------------------------------------")
    print("Attempting to start server on default port 102...")
    print("NOTE: Port 102 is a privileged port.")
    print("      You MUST run this script as ADMINISTRATOR for it to work.")
    print("----------------------------------------------------------------")
    
    try:
        server.start()
        print("Server started successfully on 0.0.0.0:102")
        print("Listening for connections...")
    except Exception as e:
        print(f"FAILED to start server: {e}")
        print("Please restart the terminal as Administrator and try again.")
        return

    print("Server is running.")
    print("Updating DB1 (Rack=0, Slot=1 or 2) every second.")
    print("  - Offset 0 (2 bytes): Counter (Int)")
    print("  - Offset 2 (4 bytes): Value (Real/Float)")
    print("Press Ctrl+C to stop.")
    
    try:
        counter = 0
        while True:
            # Update data
            # We modify the bytearray directly. 
            # struct.pack_into format: '>H' for big-endian unsigned short (standard S7 format)
            struct.pack_into('>H', db1_data, 0, counter & 0xFFFF)
            
            # Let's write a float at offset 2 (4 bytes)
            struct.pack_into('>f', db1_data, 2, float(counter) * 1.5)
            
            counter += 1
            if counter % 5 == 0:
                print(f"Updated data. Counter: {counter}")
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping...")
        server.stop()
        server.destroy()
        print("Server stopped.")

if __name__ == "__main__":
    run_server()
