import json
from http.server import ThreadingHTTPServer
import threading
import unittest
import urllib.request
import urllib.error
from tools.dashboard import Handler


class DashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.url=f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()

    def test_dashboard_and_actual_report_endpoint(self):
        with urllib.request.urlopen(self.url) as response:
            text=response.read().decode()
            self.assertIn("Connect USB device",text)
            self.assertIn('serial=(self)',response.headers['Permissions-Policy'])
        with urllib.request.urlopen(self.url+"/results") as response:
            self.assertIsInstance(json.load(response),dict)

    def test_server_does_not_expose_repository_files(self):
        for path in ("/.git/config","/tools/flash.py","/../README.md"):
            with self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(self.url+path)
            self.assertEqual(caught.exception.code,404)


if __name__=="__main__":unittest.main()
