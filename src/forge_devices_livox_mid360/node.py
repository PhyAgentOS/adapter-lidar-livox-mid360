"""Official-driver ROS2 capture backend -> real Forge Arrow outputs.

This node subscribes to a separately deployed official driver in our own ROS
domain. It does not launch existing robot scripts, SDK sessions, or algorithms.
"""

import time

from dora import Node
from forge_msgs import PolicyCommandStatus

from .codec import SensorClock, encode_cloud, encode_imu


def run(config: dict) -> None:
    if config.get("clock_confirmed") is not True:
        raise ValueError("verify sensor clock mapping and set clock_confirmed: true")
    clock = SensorClock(**config["clock"])
    # Required at startup, not inferred from the first measurement magnitude.
    acceleration_unit = config["imu_acceleration_unit"]
    if acceleration_unit not in ("g", "m_s2"):
        raise ValueError("imu_acceleration_unit must be g or m_s2")
    domain = config["ros_domain_id"]
    if isinstance(domain, bool) or not isinstance(domain, int) or not 0 <= domain <= 232:
        raise ValueError("ros_domain_id must be an integer in 0..232")
    startup_timeout = float(config["startup_timeout_seconds"])
    stream_timeout = float(config["stream_timeout_seconds"])
    if not 0 < stream_timeout <= startup_timeout < 3600:
        raise ValueError("require 0 < stream timeout <= startup timeout < 3600")
    import rclpy
    from livox_ros_driver2.msg import CustomMsg
    from rclpy.qos import QoSProfile, ReliabilityPolicy
    from sensor_msgs.msg import Imu

    rclpy.init(domain_id=domain)
    ros = rclpy.create_node("forge_mid360_capture")
    dora = Node()
    seen = set()
    started = time.monotonic()
    last_received = {}

    def status(state, message):
        dora.send_output(
            "status",
            PolicyCommandStatus(
                policy_id="mid360", command="stream", status=state, message=message
            ).to_arrow(),
        )

    def publish(stream, result):
        payload, metadata = result
        dora.send_output(stream, payload.to_arrow(), metadata)
        last_received[stream] = time.monotonic()
        seen.add(stream)
        if len(seen) == 2 and not publish.ready:
            status("running", "point cloud and IMU received; algorithm readiness is separate")
            publish.ready = True

    publish.ready = False

    ros.create_subscription(
        CustomMsg,
        config["cloud_topic"],
        lambda msg: publish("point_cloud", encode_cloud(msg, clock)),
        QoSProfile(depth=20, reliability=ReliabilityPolicy.RELIABLE),
    )
    ros.create_subscription(
        Imu,
        config["imu_topic"],
        lambda msg: publish("imu", encode_imu(msg, clock, acceleration_unit=acceleration_unit)),
        QoSProfile(depth=200, reliability=ReliabilityPolicy.RELIABLE),
    )
    status("accepted", "capture started; waiting for both sensor streams")
    try:
        for event in dora:
            if event["type"] == "STOP":
                break
            if event["type"] == "INPUT" and event["id"] == "finish":
                break
            if event["type"] == "ERROR":
                raise RuntimeError(str(event))
            # A timer keeps the event loop alive; process callbacks without a ROS thread.
            for _ in range(16):
                rclpy.spin_once(ros, timeout_sec=0.0)
            now = time.monotonic()
            for stream in ("point_cloud", "imu"):
                if stream not in last_received:
                    if now - started > startup_timeout:
                        raise TimeoutError(f"{stream} not received during startup")
                elif now - last_received[stream] > stream_timeout:
                    raise TimeoutError(f"{stream} input timed out")
    except Exception as exc:
        status("error", str(exc))
        raise
    finally:
        ros.destroy_node()
        rclpy.shutdown()
