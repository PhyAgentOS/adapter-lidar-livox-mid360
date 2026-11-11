"""Validate the external ROS2 runtime without opening sensor or chassis devices."""

import importlib
import sys


def check_runtime():
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError("ROS2 Jazzy requires the Python 3.12 ABI")
    for name in ["rclpy", "livox_ros_driver2.msg", "sensor_msgs.msg"]:
        module = importlib.import_module(name)
        if name.endswith((".msg", ".srv", ".action")):
            from rclpy.type_support import check_for_type_support

            for value in vars(module).values():
                if isinstance(value, type) and hasattr(type(value), "__import_type_support__"):
                    check_for_type_support(value)
