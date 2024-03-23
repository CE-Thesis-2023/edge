import logging
import unittest
import json
from edge.config import EdgeConfig


class TestEdgeConfig(unittest.TestCase):
    def test_parse(self):
        config = EdgeConfig()
        c = config.parse_file(config_file="./edge/config.yaml")
        print(str(c.cameras))
        self.assertIsNotNone(obj=c)
