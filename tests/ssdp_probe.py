import socket
import time

s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
s.settimeout(.5)
s.sendto(b'M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\nMAN: "ssdp:discover"\r\nMX: 1\r\nST: ssdp:all\r\n\r\n',('239.255.255.250',1900))
end = time.monotonic()+5
while time.monotonic()<end:
    try:
        response,address = s.recvfrom(8192)
        if 'HiFi' in response.decode() or address[0] == '192.168.1.207':
            print(address,response.decode())
    except socket.timeout:
        pass
