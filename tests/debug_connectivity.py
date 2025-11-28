import socket
import sys

def check_port(ip, port):
    print(f"Checking {ip}:{port}...", end='')
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    try:
        result = s.connect_ex((ip, port))
        if result == 0:
            print(" OPEN")
            s.close()
            return True
        else:
            print(f" CLOSED (Err: {result})")
            s.close()
            return False
    except Exception as e:
        print(f" ERROR ({e})")
        return False

print("Connectivity Check:")
check_port("127.0.0.1", 102)
check_port("127.0.0.1", 1102)
check_port("localhost", 102)
check_port("localhost", 1102)
