# -*- coding: utf8 -*-
"""
Tests for connection parameters.
"""
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from pika import ConnectionParameters


class ConnectionParametersUriTests(unittest.TestCase):

    def test_full(self):
        uri = 'amqp://user:pass@host:10000/vhost'
        params = ConnectionParameters(uri=uri)

        self.assertEqual(params.host, 'host')
        self.assertEqual(params.port, 10000)
        self.assertEqual(params.credentials.username, 'user')
        self.assertEqual(params.credentials.password, 'pass')
        self.assertEqual(params.virtual_host, 'vhost')

    def test_encoded(self):
        uri = "amqp://user%61:%61pass@ho%61st:10000/v%2fhost"
        params = ConnectionParameters(uri=uri)

        self.assertEqual(params.host, 'hoast')
        self.assertEqual(params.port, 10000)
        self.assertEqual(params.credentials.username, 'usera')
        self.assertEqual(params.credentials.password, 'apass')
        self.assertEqual(params.virtual_host, 'v/host')

    def test_scheme_only(self):
        uri = "amqp://"
        params = ConnectionParameters(uri=uri)

        self.assertEqual(params.host, 'localhost')
        self.assertEqual(params.port, 5672)
        self.assertEqual(params.credentials.username, 'guest')
        self.assertEqual(params.credentials.password, 'guest')
        self.assertEqual(params.virtual_host, '/')

    def test_delimiters_no_effect(self):
        uri = "amqp://:@/"
        params = ConnectionParameters(uri=uri)

        self.assertEqual(params.host, 'localhost')
        self.assertEqual(params.port, 5672)
        self.assertEqual(params.credentials.username, 'guest')
        self.assertEqual(params.credentials.password, 'guest')
        self.assertEqual(params.virtual_host, '/')

    def test_user_only_no_effect(self):
        uri = "amqp://user@"
        params = ConnectionParameters(uri=uri)

        self.assertEqual(params.host, 'localhost')
        self.assertEqual(params.port, 5672)
        self.assertEqual(params.credentials.username, 'guest')
        self.assertEqual(params.credentials.password, 'guest')
        self.assertEqual(params.virtual_host, '/')

    def test_full_credentials(self):
        uri = "amqp://user:pass@"
        params = ConnectionParameters(uri=uri)

        self.assertEqual(params.host, 'localhost')
        self.assertEqual(params.port, 5672)
        self.assertEqual(params.credentials.username, 'user')
        self.assertEqual(params.credentials.password, 'pass')
        self.assertEqual(params.virtual_host, '/')

    def test_host_only(self):
        uri = "amqp://host"
        params = ConnectionParameters(uri=uri)

        self.assertEqual(params.host, 'host')
        self.assertEqual(params.port, 5672)
        self.assertEqual(params.credentials.username, 'guest')
        self.assertEqual(params.credentials.password, 'guest')
        self.assertEqual(params.virtual_host, '/')

    def test_port_only(self):
        uri = "amqp://:10000"
        params = ConnectionParameters(uri=uri)

        self.assertEqual(params.host, 'localhost')
        self.assertEqual(params.port, 10000)
        self.assertEqual(params.credentials.username, 'guest')
        self.assertEqual(params.credentials.password, 'guest')
        self.assertEqual(params.virtual_host, '/')

    def test_virtual_host_only(self):
        uri = "amqp:///vhost"
        params = ConnectionParameters(uri=uri)

        self.assertEqual(params.host, 'localhost')
        self.assertEqual(params.port, 5672)
        self.assertEqual(params.credentials.username, 'guest')
        self.assertEqual(params.credentials.password, 'guest')
        self.assertEqual(params.virtual_host, 'vhost')

    def test_host_and_no_vhost(self):
        uri = "amqp://host/"
        params = ConnectionParameters(uri=uri)

        self.assertEqual(params.host, 'host')
        self.assertEqual(params.port, 5672)
        self.assertEqual(params.credentials.username, 'guest')
        self.assertEqual(params.credentials.password, 'guest')
        self.assertEqual(params.virtual_host, '/')

    def test_host_and_vhost(self):
        uri = "amqp://host/%2f"
        params = ConnectionParameters(uri=uri)

        self.assertEqual(params.host, 'host')
        self.assertEqual(params.port, 5672)
        self.assertEqual(params.credentials.username, 'guest')
        self.assertEqual(params.credentials.password, 'guest')
        self.assertEqual(params.virtual_host, '/')

    def test_ipv6(self):
        uri = "amqp://[::1]"
        params = ConnectionParameters(uri=uri)

        self.assertEqual(params.host, '::1')
        self.assertEqual(params.port, 5672)
        self.assertEqual(params.credentials.username, 'guest')
        self.assertEqual(params.credentials.password, 'guest')
        self.assertEqual(params.virtual_host, '/')

    def test_wrong_scheme(self):
        uri = 'xxxx://user:pass@host:10000/vhost'
        self.assertRaises(ValueError, ConnectionParameters, uri=uri)

    def test_no_scheme(self):
        uri = 'user:pass@host:10000/vhost'
        self.assertRaises(ValueError, ConnectionParameters, uri=uri)

    def test_ssl_scheme(self):
        uri = 'amqps://user:pass@host:10000/vhost'
        params = ConnectionParameters(uri=uri)
        self.assertEqual(params.ssl, True)
