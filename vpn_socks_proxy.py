import asyncio
import logging
import socket
import struct

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

VPN_INTERFACE_IP = '10.2.0.2'
LISTEN_HOST = '127.0.0.1'
LISTEN_PORT = 8080

class Socks5Proxy:
    def __init__(self, host, port, bind_ip):
        self.host = host
        self.port = port
        self.bind_ip = bind_ip

    async def handle_client(self, reader, writer):
        try:
            # SOCKS5 Handshake
            version = await reader.read(1)
            if not version or version != b'\x05':
                writer.close()
                return

            nmethods = await reader.read(1)
            methods = await reader.read(ord(nmethods))

            # We only support no auth (0x00)
            writer.write(b'\x05\x00')
            await writer.drain()

            # Request
            version = await reader.read(1) # 0x05
            cmd = await reader.read(1) # 0x01 (CONNECT)
            rsv = await reader.read(1) # 0x00
            atyp = await reader.read(1) # Address Type

            if cmd != b'\x01': # Only CONNECT supported
                writer.close()
                return

            if atyp == b'\x01': # IPv4
                addr = socket.inet_ntoa(await reader.read(4))
            elif atyp == b'\x03': # Domain
                domain_len = ord(await reader.read(1))
                addr = (await reader.read(domain_len)).decode()
            elif atyp == b'\x04': # IPv6
                addr = socket.inet_ntop(socket.AF_INET6, await reader.read(16))
            else:
                writer.close()
                return

            port_bytes = await reader.read(2)
            port = struct.unpack('>H', port_bytes)[0]

            logger.info(f"Connecting to {addr}:{port} via {self.bind_ip}")

            try:
                # Connect to remote target binding to VPN IP
                remote_reader, remote_writer = await asyncio.open_connection(
                    host=addr, 
                    port=port, 
                    local_addr=(self.bind_ip, 0)
                )
            except Exception as e:
                logger.error(f"Failed to connect to remote {addr}:{port}: {e}")
                # Reply with error (0x04 host unreachable)
                writer.write(b'\x05\x04\x00\x01\x00\x00\x00\x00\x00\x00')
                await writer.drain()
                writer.close()
                return

            # Reply success (0x00)
            # Bind address/port in reply are usually ignored by clients, sending 0s
            writer.write(b'\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00')
            await writer.drain()

            # Pipe data
            await asyncio.gather(
                self.pipe(reader, remote_writer),
                self.pipe(remote_reader, writer)
            )

        except Exception as e:
            logger.error(f"Proxy error: {e}")
        finally:
            writer.close()

    async def pipe(self, reader, writer):
        try:
            while not reader.at_eof():
                data = await reader.read(8192)
                if not data:
                    break
                writer.write(data)
                await writer.drain()
        except Exception:
            pass
        finally:
            writer.close()

    async def start(self):
        server = await asyncio.start_server(
            self.handle_client, self.host, self.port
        )
        logger.info(f"SOCKS5 Proxy listening on {self.host}:{self.port}, binding outgoing to {self.bind_ip}")
        async with server:
            await server.serve_forever()

if __name__ == '__main__':
    proxy = Socks5Proxy(LISTEN_HOST, LISTEN_PORT, VPN_INTERFACE_IP)
    try:
        asyncio.run(proxy.start())
    except KeyboardInterrupt:
        pass
