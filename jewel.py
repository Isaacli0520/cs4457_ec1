#!/usr/bin/env python3

import socket
import select
import sys
import queue
import datetime

from file_reader import FileReader
from os.path import splitext
import os

class Jewel:
    default_headers = {
        "Server":"Jewel Server il5fq",
        "Content-Type": "text/html",
    }

    file_types = {
        ".html":"text/html",
        ".css":"text/css",
        ".png":"text/png",
        ".jpeg":"image/jpeg",
        ".jpg":"image/jpeg",
        ".gif":"image/gif",
        ".txt":"text/plain",
    }

    http_status_codes = {
        200:"OK",
        400:"Bad Request",
        401:"Unauthorized",
        403:"Forbidden",
        404:"Not Found",
        500:"Internal Server Error",
    }

    weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep","Oct", "Nov", "Dec"]

    def __init__(self, port, file_path, file_reader):
        self.file_path = file_path
        self.file_reader = file_reader

        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(('0.0.0.0', port))

        server.listen(5)

        rlist, wlist, errlist = [server], [], []
        msgs = {}

        while True:
            rd, wrt, err = select.select(rlist, wlist, errlist)
            for s in rd:
                if s == server:
                    (client, address) = s.accept()
                    print("[CONN] Connection from %s on port %s" % address)
                    rlist.append(client)
                    msgs[client] = queue.Queue()
                else:
                    data = s.recv(1024)
                    if data:
                        msgs[s].put(self.handle_request(data, s.getpeername()), False)
                        if s not in wlist:
                            wlist.append(s)
                    else:
                        if s in wlist:
                            wlist.remove(s)
                        rlist.remove(s)
                        msgs.pop(s, None)
                        s.close()
            for s in wrt:
                try:
                    msg = msgs[s].get(False)
                except queue.Empty:
                    wlist.remove(s)
                else:
                    s.sendall(msg)
            for s in err:
                if s in rlist:
                    rlist.remove(s)
                if s in wlist:
                    wlist.remove(s)
                msgs.pop(s, None)
                s.close()

    def handle_request(self, req, addr_port):
        request = req.decode('utf-8')
        fields, req_headers = self.parse_http_request(request, addr_port)
        if not fields and not req_headers:
            print("[ERRO] [%s:%s] Invalid request returned error 400" % (addr_port[0], addr_port[1]))
            resp_start_line = "%s %s %s\r\n" % ("HTTP/1.1", 400, self.http_status_codes[400])
            resp_headers = self.get_response_headers()
            return resp_start_line.encode() + resp_headers.encode()
        method, path, protocal = fields
        path = os.path.join(self.file_path, path.strip("/"))
        headers = {}
        if method == "GET":
            if os.path.isdir(path):
                status_code = 200
                body = ("<html><body><h1>%s</h1></body></html>" % path).encode()
            else:
                body = self.file_reader.get(path, req_headers.get("Cookie"))
                if body:
                    name, extension = splitext(path)
                    headers["Content-Type"] = self.file_types[extension]
                    status_code = 200
                else:
                    print("[ERRO] [%s:%s] %s request returned error 404" % (addr_port[0], addr_port[1], fields[0]))
                    status_code = 404
                    body = "<html><body><h1>404 not found</h1></body></html>".encode()
            headers["Content-Length"] = len(body)
        elif method == "HEAD":
            if os.path.isdir(path):
                status_code = 200
                headers["Content-Length"] = len(("<html><body><h1>%s</h1></body></html>" % path).encode())
            else:
                content_len = self.file_reader.head(path, req_headers.get("Cookie"))
                if content_len:
                    name, extension = splitext(path)
                    headers["Content-Type"] = self.file_types[extension]
                    headers["Content-Length"] = content_len
                    status_code = 200
                else:
                    status_code = 404
                    headers["Content-Length"] = len("<html><body><h1>404 not found</h1></body></html>".encode())
        resp_start_line = "%s %s %s\r\n" % (protocal, status_code, self.http_status_codes[status_code])
        resp_headers = self.get_response_headers(headers)
        resp_body = body if method == "GET" else b""
        return resp_start_line.encode() + resp_headers.encode() + resp_body

    def get_date(self, date):
        weekday = self.weekdays[date.weekday()]
        month = self.months[date.month - 1]
        return "%s, %02d %s %04d %02d:%02d:%02d GMT" % (weekday, date.day, month, date.year, date.hour, date.minute, date.second)

    def get_response_headers(self, headers = {}):
        d = self.default_headers.copy()
        d["Date"] = self.get_date(datetime.datetime.utcnow())
        if headers:
            d.update(headers)
        return "".join(["%s: %s\r\n" % (k, v) for k, v in d.items()]) + "\r\n"


    def parse_http_request(self, request, addr_port):
        header_end = request.find('\r\n\r\n')
        if header_end > -1:
            header_string = request[:header_end]
            lines = header_string.split('\r\n')

            request_fields = lines[0].split()
            print("[REQU] [%s:%s] %s request for %s" % (addr_port[0], addr_port[1], request_fields[0], request_fields[1]))
            headers = {}
            for header in lines[1:]:
                header_fields = header.split(':')
                key = header_fields[0].strip()
                val = header_fields[1].strip()
                headers[key] = val
            return request_fields, headers
        return None, None



if __name__ == "__main__":
    port = int(sys.argv[1])
    file_path = sys.argv[2]

    FR = FileReader()

    J = Jewel(port, file_path, FR)
