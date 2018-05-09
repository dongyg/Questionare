# -*- coding: utf-8 -*-
# Author: Johan Hanssen Seferidis
# License: MIT
# Modify: DongYiguang. for web.py

'''
这个实现方法是响应GET请求后进行WebSocket握手，成功后无限循环，获取客户端发送数据以及回复和发出数据。这样会挂起阻塞webpy为这个请求而运行的线程。
实测(命令行运行)，通过webpy自己的CherryPyWSGIServer提供httpserver服务
  1.达到5个客户端后，系统响应变慢（第5个websocket接入有点慢，第6个网页打开开始变慢websocket接入更慢）
  2.达到7个客户端，发消息时总会有1/2个客户端收不到消息
  3.开到10个客户端，webpy就不再响应任何请求了。通过调试web.httpserver.server.stats中的内容可以发现，ThreadsIdle是0了（CherryPyWSGIServer初始化的numthreads就是10个）
  4.修改 httpserver 中的 runsimple 函数，设置 server.numthreads = 20 后发现可容纳客户端20个，超过20个同上一条。因此客户端容量取决于HTTPServer的requests的线程池的线程个数
实测(用Apache部署)，走wsgi规范接口
  1.不能使用。因为wsgi接口中env只有wsgi.input，通过它可以访问到socket通讯的rfile，但没有用来“写”的接口，拿不到socket的wfile，因此在wsgi这一层无法做到socket通讯下发数据
结论：本方法只能适用于命令行运行方式
'''

__all__ = ['WebSocketHandler']

import re, sys
import struct
from base64 import b64encode
from hashlib import sha1
import time

if sys.version_info[0] < 3 :
    from SocketServer import ThreadingMixIn, TCPServer, StreamRequestHandler
else:
    from socketserver import ThreadingMixIn, TCPServer, StreamRequestHandler

import webapi as web

'''
+-+-+-+-+-------+-+-------------+-------------------------------+
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-------+-+-------------+-------------------------------+
|F|R|R|R| opcode|M| Payload len |    Extended payload length    |
|I|S|S|S|  (4)  |A|     (7)     |             (16/64)           |
|N|V|V|V|       |S|             |   (if payload len==126/127)   |
| |1|2|3|       |K|             |                               |
+-+-+-+-+-------+-+-------------+ - - - - - - - - - - - - - - - +
|     Extended payload length continued, if payload len == 127  |
+ - - - - - - - - - - - - - - - +-------------------------------+
|                     Payload Data continued ...                |
+---------------------------------------------------------------+
'''

FIN    = 0x80
OPCODE = 0x0f
MASKED = 0x80
PAYLOAD_LEN = 0x7f
PAYLOAD_LEN_EXT16 = 0x7e
PAYLOAD_LEN_EXT64 = 0x7f

OPCODE_TEXT = 0x01
CLOSE_CONN  = 0x8
PING = 0x9
PONG = 0xA

class WebSocketHandler:
    def __init__(self):
        if not web.ctx.env.has_key('REQUEST_OBJ'):
            raise Exception('Only could be run by [python *.wsig] under shell.')
        self.request = web.ctx.env['REQUEST_OBJ']
        self.rfile = self.request.rfile
        self.wfile = self.request.conn.wfile
        self.keep_alive = True
        self.handshake_done = False
        self.valid_client = False

    # -------------------------------- Handle ---------------------------------
    def GET(self):
        while self.keep_alive:
            try:
                if not self.handshake_done:
                    self.handshake()
                elif self.valid_client:
                    self.read_next_message()
                    time.sleep(0.01)
            except (KeyboardInterrupt, SystemExit):
                break
        self._client_left_(self)

    def read_bytes(self, num):
        # python3 gives ordinal of byte directly
        bytes = self.rfile.read_whatever(num)
        if not bytes: return bytes
        if sys.version_info[0] < 3:
            return map(ord, bytes)
        else:
            return bytes

    def read_next_message(self):

        ret = self.read_bytes(2)
        if not ret: return
        b1, b2 = ret

        fin    = b1 & FIN
        opcode = b1 & OPCODE
        masked = b2 & MASKED
        payload_length = b2 & PAYLOAD_LEN

        if not b1:
            print("Client closed connection.")
            self.keep_alive = 0
            return
        if opcode == CLOSE_CONN:
            print("Client asked to close connection.")
            self.keep_alive = 0
            return
        if not masked:
            print("Client must always be masked.")
            self.keep_alive = 0
            return

        if payload_length == 126:
            payload_length = struct.unpack(">H", self.rfile.read_whatever(2))[0]
        elif payload_length == 127:
            payload_length = struct.unpack(">Q", self.rfile.read_whatever(8))[0]

        masks = self.read_bytes(4)
        decoded = ""
        for char in self.read_bytes(payload_length):
            char ^= masks[len(decoded) % 4]
            decoded += chr(char)
        self._message_received_(self, decoded)

    def _send_message(self, message):
        self.send_text(message)

    def send_text(self, message):
        '''
        NOTES
        Fragmented(=continuation) messages are not being used since their usage
        is needed in very limited cases - when we don't know the payload length.
        '''

        # Validate message
        if isinstance(message, bytes):
            message = try_decode_UTF8(message) # this is slower but assures we have UTF-8
            if not message:
                print("Can\'t send message, message is not valid UTF-8")
                return False
        elif isinstance(message, str) or isinstance(message, unicode):
            pass
        else:
            print('Can\'t send message, message has to be a string or bytes. Given type is %s' % type(message))
            return False

        header  = bytearray()
        payload = encode_to_UTF8(message)
        payload_length = len(payload)

        # Normal payload
        if payload_length <= 125:
            header.append(FIN | OPCODE_TEXT)
            header.append(payload_length)

        # Extended payload
        elif payload_length >= 126 and payload_length <= 65535:
            header.append(FIN | OPCODE_TEXT)
            header.append(PAYLOAD_LEN_EXT16)
            header.extend(struct.pack(">H", payload_length))

        # Huge extended payload
        elif payload_length < 18446744073709551616:
            header.append(FIN | OPCODE_TEXT)
            header.append(PAYLOAD_LEN_EXT64)
            header.extend(struct.pack(">Q", payload_length))

        else:
            raise Exception("Message is too big. Consider breaking it into chunks.")
            return

        try:
            self.wfile.send(header + payload)
        except Exception, e:
            client = self.handler_to_client(self)
            print client['id'],' is miss.'
            self.keep_alive = 0
            # self._client_left_(self)

    def handshake(self):
        # headers = self.request.inheaders
        if web.ctx.env.get('HTTP_UPGRADE')!='websocket':
            self.keep_alive = False
            return ''
        key = web.ctx.env.get('HTTP_SEC_WEBSOCKET_KEY')
        if not key:
            print("Client tried to connect but was missing a key")
            self.keep_alive = False
            return ''
        response = self.make_handshake_response(key)
        self.handshake_done = self.wfile.send(response.encode())
        self.valid_client = True
        self._new_client_(self,(web.ctx.env['REMOTE_ADDR'],web.ctx.env['REMOTE_PORT']))

    def make_handshake_response(self, key):
        return \
          'HTTP/1.1 101 Switching Protocols\r\n'\
          'Upgrade: websocket\r\n'              \
          'Connection: Upgrade\r\n'             \
          'Sec-WebSocket-Accept: %s\r\n'        \
          '\r\n' % self.calculate_response_key(key)

    def calculate_response_key(self, key):
        GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
        hash = sha1(key.encode() + GUID.encode())
        response_key = b64encode(hash.digest()).strip()
        return response_key.decode('ASCII')

    # -------------------------------- Manage ---------------------------------
    # clients is a list of dict: {'id':id,'handler':handler,'address':(addr,port)}
    clients = []
    id_counter = 0
    def _message_received_(self, handler, msg):
        self.message_received(self.handler_to_client(handler), msg)
    def _new_client_(self, handler, address):
        WebSocketHandler.id_counter += 1
        client = {
            'id'      : WebSocketHandler.id_counter,
            'handler' : handler,
            'address' : address
        }
        self.clients.append(client)
        self.new_client(client)
    def _client_left_(self, handler):
        client = self.handler_to_client(handler)
        self.client_left(client)
        if client in self.clients:
            self.clients.remove(client)
    def _unicast_(self, to_client, msg):
        to_client['handler']._send_message(msg)
    def _multicast_(self, msg):
        import copy
        dup = copy.copy(self.clients)
        for client in dup:
            self._unicast_(client, msg)
    def handler_to_client(self, handler):
        for client in self.clients:
            if client['handler'] == handler:
                return client

    # -------------------------------- API ---------------------------------
    def new_client(self, client):
        pass
    def client_left(self, client):
        pass
    def message_received(self, client, message):
        pass
    def set_fn_new_client(self, fn):
        self.new_client=fn
    def set_fn_client_left(self, fn):
        self.client_left=fn
    def set_fn_message_received(self, fn):
        self.message_received=fn
    def send_message(self, client, msg):
        self._unicast_(client, msg)
    def send_message_to_all(self, msg):
        self._multicast_(msg)
    def send_message_except(self, msg, client):
        import copy
        dup = copy.copy(self.clients)
        for c in dup:
            if c['id']!=client['id']:
                self._unicast_(c, msg)

def encode_to_UTF8(data):
    try:
        return data.encode('UTF-8')
    except UnicodeEncodeError as e:
        print("Could not encode data to UTF-8 -- %s" % e)
        return False
    except Exception as e:
        raise(e)
        return False

def try_decode_UTF8(data):
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError:
        return False
    except Exception as e:
        raise(e)

