import socket
import webbrowser
from threading import Timer
import os
from app import create_app
import subprocess
from urllib.request import urlopen 
from requests import get


app = create_app()

def find_ip():
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
        ip = get('https://api.ipify.org').text
        s.connect((ip,80))
        return s.getsockname()[0]

def find_available_port(host):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return sock.getsockname()[1]

def main():
    host = find_ip()
    port = find_available_port(host)
    chrome=["start","Chrome","--app",f"--app=http://{host}:{port}"]
    edge=["start","msedge","--app",f"--app=http://{host}:{port}"]
    try:
        subprocess.call(args=chrome,shell=True) 
        print(chrome)
    except Exception as ex:
        print(ex)
        subprocess.call(args=edge,shell=True)
        print(edge) 
      
    try:
        from waitress import serve
        serve(app, host="0.0.0.0", port=port, threads=4)
    except ImportError as ie:
        print(ie)
        app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False, threaded=True)


if __name__ == "__main__":
    main()




# Functions:

# socket() -- create a new socket object
# socketpair() -- create a pair of new socket objects [*]
# fromfd() -- create a socket object from an open file descriptor [*]
# send_fds() -- Send file descriptor to the socket.
# recv_fds() -- Receive file descriptors from the socket.
# fromshare() -- create a socket object from data received from socket.share() [*]
# gethostname() -- return the current hostname
# gethostbyname() -- map a hostname to its IP number
# gethostbyaddr() -- map an IP number or hostname to DNS info
# getservbyname() -- map a service name and a protocol name to a port number
# getprotobyname() -- map a protocol name (e.g. 'tcp') to a number
# ntohs(), ntohl() -- convert 16, 32 bit int from network to host byte order
# htons(), htonl() -- convert 16, 32 bit int from host to network byte order
# inet_aton() -- convert IP addr string (123.45.67.89) to 32-bit packed format
# inet_ntoa() -- convert 32-bit packed format IP to string (123.45.67.89)
# socket.getdefaulttimeout() -- get the default timeout value
# socket.setdefaulttimeout() -- set the default timeout value
# create_connection() -- connects to an address, with an optional timeout and
#                        optional source address.
# create_server() -- create a TCP socket and bind it to a specified address.