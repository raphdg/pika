# ***** BEGIN LICENSE BLOCK *****
#
# For copyright and licensing please refer to COPYING.
#
# ***** END LICENSE BLOCK *****

"""
Pika provides multiple adapters to connect to RabbitMQ:

- adapters.select_connection.SelectConnection: A native event based connection
  adapter that implements select, kqueue, poll and epoll.
- adapters.asyncore_connection.AsyncoreConnection: Legacy adapter kept for
  convenience of previous Pika users. It is recommended to use the
  SelectConnection instead of AsyncoreConnection.
- adapters.tornado_connection.TornadoConnection: Connection adapter for use
  with the Tornado web framework.
- adapters.blocking_connection.BlockingConnection: Enables blocking,
  synchronous operation on top of library for simple uses. This is not
  recommended and is included for legacy reasons only.
"""

import errno
import socket
import time

# See if we have SSL support
try:
    import ssl
    SSL = True
except ImportError:
    SSL = False

from pika.connection import Connection
import pika.log

# Use epoll's constants to keep life easy
READ = 0x0001
WRITE = 0x0004
ERROR = 0x0008


class BaseConnection(Connection):

    def __init__(self, parameters=None,
                  on_open_callback=None,
                 reconnection_strategy=None):

        # Let the developer know we could not import SSL
        if parameters.ssl and not SSL:
            raise Exception("SSL specified but it is not available")

        # Set our defaults
        self.fd = None
        self.ioloop = None
        self.socket = None
        self._ssl_connecting = False
        self._ssl_handshake = False

        # Event states (base and current)
        self.base_events = READ | ERROR
        self.event_state = self.base_events

        # Call our parent's __init__
        Connection.__init__(self, parameters, on_open_callback,
                            reconnection_strategy)

    def _adapter_connect(self, host, port):
        """
        Base connection function to be extended as needed
        """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self.socket.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
        # Wrap the SSL socket if we SSL turned on
        ssl_text = ""
        if self.parameters.ssl:
            ssl_text = " with SSL"
            if self.parameters.ssl_options:
                # Always overwrite this value
                self.parameters.ssl_options['do_handshake_on_connect'] = \
                    self._ssl_handshake
                self.socket = ssl.wrap_socket(self.socket,
                                              **self.parameters.ssl_options)
            else:
                self.socket = ssl.wrap_socket(self.socket,
                                              do_handshake_on_connect=\
                                                  self._ssl_handshake)

            # Flags for SSL handshake negotiation
            self._ssl_connecting = True

        # Try and connect
        pika.log.info("Connecting to %s:%i%s", host, port, ssl_text)

        self.socket.connect((host, port))
        self.socket.setblocking(0)

    def add_timeout(self, delay_sec, callback):
        deadline = time.time() + delay_sec
        return self.ioloop.add_timeout(deadline, callback)

    def remove_timeout(self, timeout_id):
        self.ioloop.remove_timeout(timeout_id)

    def _erase_credentials(self):
        pass

    def _flush_outbound(self):
        """
        Call the state manager who will figure out that we need to write.
        """
        self._manage_event_state()

    def _adapter_disconnect(self):
        """
        Called if we are forced to disconnect for some reason from Connection
        """
        # Remove from the IOLoop
        self.ioloop.stop()

        # Close our socket
        self.socket.close()

    def _handle_disconnect(self):
        """
        Called internally when we know our socket is disconnected already
        """
        # Remove from the IOLoop
        self.ioloop.stop()

        # Close up our Connection state
        self._on_connection_closed(None, True)

    def _handle_error(self, error):
        """
        Internal error handling method. Here we expect a socket.error coming in
        and will handle different socket errors differently.
        """
        # Handle version differences in Python
        if hasattr(error, 'errno'):  # Python >= 2.6
            error_code = error.errno
        else:
            error_code = error[0]  # Python <= 2.5

        # Ok errors, just continue what we were doing before
        if error_code in (errno.EWOULDBLOCK, errno.EAGAIN, errno.EINTR):
            return
        # Socket is closed, so lets just go to our handle_close method
        elif error_code == errno.EBADF:
            pika.log.error("%s: Socket is closed", self.__class__.__name__)
            self._handle_disconnect()
            return None

        elif self.parameters.ssl and isinstance(error, ssl.SSLError):
            pika.log.error(repr(error))
            if error_code in (ssl.SSL_ERROR_WANT_READ,
                              ssl.SSL_ERROR_WANT_WRITE):
                return None
            else:
                pika.log.error("%s: SSL Socket error on fd %d: %s",
                        self.__class__.__name__,
                        self.socket.fileno(),
                        repr(error))
        else:
            # Haven't run into this one yet, log it.
            pika.log.error("%s: Socket Error on %d: %s",
                           self.__class__.__name__,
                           self.socket.fileno(),
                           error_code)

        # Disconnect from our IOLoop and let Connection know what's up
        self._handle_disconnect()

    def _do_ssl_handshake(self):
        """
        Copied from python stdlib test_ssl.py

        """
        pika.log.debug("_do_ssl_handshake")
        try:
            self.socket.do_handshake()
        except ssl.SSLError, err:
            if err.args[0] in (ssl.SSL_ERROR_WANT_READ,
                               ssl.SSL_ERROR_WANT_WRITE):
                return
            elif err.args[0] == ssl.SSL_ERROR_EOF:
                return self.handle_close()
            raise
        except socket.error, err:
            if err.args[0] == errno.ECONNABORTED:
                return self.handle_close()
        else:
            self._ssl_connecting = False

    def _handle_events(self, fd, events, error=None):
        """
        Our IO/Event loop have called us with events, so process them
        """
        if not self.socket:
            pika.log.error("%s: Got events for closed stream %d",
                           self.__class__.__name__, self.socket.fileno())
            return

        if events & READ:
            self._handle_read()

        if events & ERROR:
            self._handle_error(error)

        if events & WRITE:
            self._handle_write()

            # Call our event state manager who will decide if we reset our
            # event state due to having an empty outbound buffer
            self._manage_event_state()

    def _handle_read(self):
        """
        Read from the socket and call our on_data_available with the data
        """
        if self.parameters.ssl and self._ssl_connecting:
            return self._do_ssl_handshake()
        try:
            if self.parameters.ssl and self.socket.pending():
                data = self.socket.read(self._suggested_buffer_size)
                
                while len(data) == 0:
                    data = self.socket.read(self._suggested_buffer_size)
            else:
                data = self.socket.recv(self._suggested_buffer_size)
        except socket.timeout:
            raise
        except socket.error, error:
            return self._handle_error(error)

        # We received no data, so disconnect
        if not data:
            return self._adapter_disconnect()

        # Pass the data into our top level frame dispatching method
        self._on_data_available(data)

    def _handle_write(self):
        """
        We only get here when we have data to write, so try and send
        Pika's suggested buffer size of data (be nice to Windows)
        """
        if self.parameters.ssl and self._ssl_connecting:
            return self._do_ssl_handshake()

        data = self.outbound_buffer.read(self._suggested_buffer_size)
        try:
            if self.parameters.ssl:
                bytes_written = 0
                while bytes_written == 0:
                    bytes_written = self.socket.send(data)
            else:
                bytes_written = self.socket.send(data)
        except socket.timeout:
            raise
        except socket.error, error:
            return self._handle_error(error)

        # Remove the content from our output buffer
        self.outbound_buffer.consume(bytes_written)

    def _manage_event_state(self):
        """
        We use this to manage the bitmask for reading/writing/error which
        we want to use to have our io/event handler tell us when we can
        read/write, etc
        """
        # Do we have data pending in the outbound buffer?
        if self.outbound_buffer.size:

            # If we don't already have write in our event state append it
            # otherwise do nothing
            if not self.event_state & WRITE:

                # We can assume that we're in our base_event state
                self.event_state |= WRITE

                # Update the IOLoop
                self.ioloop.update_handler(self.socket.fileno(),
                                           self.event_state)

        # We don't have data in the outbound buffer
        elif self.event_state & WRITE:

            # Set our event state to the base events
            self.event_state = self.base_events

            # Update the IOLoop
            self.ioloop.update_handler(self.socket.fileno(), self.event_state)
