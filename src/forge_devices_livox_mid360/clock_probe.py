"""Read-only live Livox clock/unit inspection for managed MID-360 capture."""

import re
import time

import numpy as np


def scout(domain, cloud_topic, imu_topic, driver_log, acceleration_unit="g"):
    import rclpy
    from livox_ros_driver2.msg import CustomMsg
    from rclpy.qos import QoSProfile, ReliabilityPolicy
    from sensor_msgs.msg import Imu

    rclpy.init(domain_id=domain)
    node = rclpy.create_node("forge_mid360_clock_inspection")
    cloud_stamps, imu_stamps, offsets, norms = [], [], [], []

    def stamp(header):
        return header.stamp.sec * 10**9 + header.stamp.nanosec

    def cloud(msg):
        if msg.point_num != len(msg.points) or not msg.point_num:
            raise ValueError("invalid real cloud count")
        if stamp(msg.header) != msg.timebase:
            raise ValueError("real cloud header and timebase disagree")
        cloud_stamps.append(int(msg.timebase))

    def imu(msg):
        ns = stamp(msg.header)
        imu_stamps.append(ns)
        offsets.append(time.time_ns() - ns)
        a = msg.linear_acceleration
        norms.append((a.x * a.x + a.y * a.y + a.z * a.z) ** 0.5)

    qos = QoSProfile(depth=512, reliability=ReliabilityPolicy.RELIABLE)
    node.create_subscription(CustomMsg, cloud_topic, cloud, qos)
    node.create_subscription(Imu, imu_topic, imu, qos)
    started = time.monotonic()
    try:
        while time.monotonic() - started < 15:
            rclpy.spin_once(node, timeout_sec=0.05)
            if len(cloud_stamps) >= 30 and len(imu_stamps) >= 400:
                break
    finally:
        node.destroy_node()
        rclpy.shutdown()
    if len(cloud_stamps) < 20 or len(imu_stamps) < 200:
        raise TimeoutError(
            f"insufficient real input: cloud={len(cloud_stamps)}, imu={len(imu_stamps)}"
        )
    if min(np.diff(cloud_stamps)) <= 0 or min(np.diff(imu_stamps)) <= 0:
        raise ValueError("real input sample time is not strictly increasing")
    types = set(
        int(v)
        for v in re.findall(
            r"FORGE_SENSOR_CLOCK type=(\d+)", driver_log.read_text(errors="replace")
        )
    )
    if len(types) != 1 or not types <= {0, 1, 2}:
        raise ValueError(f"sensor clock type unknown or changed: {types}")
    kind = types.pop()
    acceleration_norm = float(np.median(norms))
    expected = 1.0 if acceleration_unit == "g" else 9.80665
    if not 0.5 * expected < acceleration_norm < 1.5 * expected:
        raise ValueError(
            f"raw acceleration not consistent with stationary g units: {acceleration_norm}"
        )
    # This is a fixed host-epoch anchor, not a PTP accuracy claim. Raw timestamps
    # and all inter-sample intervals remain unchanged in Forge metadata.
    offset = int(min(offsets)) if kind == 0 else 0
    if kind in (1, 2) and abs(int(np.median(offsets))) > 1_000_000_000:
        raise ValueError("synchronized sensor timestamps differ from host by more than 1 s")
    return {
        "time_type": kind,
        "domain": "livox_device_uptime" if kind == 0 else "livox_synchronized",
        "offset_ns": offset,
        "raw_acceleration_norm": acceleration_norm,
        "anchor_method": "minimum_observed_imu_receive_offset" if kind == 0 else "sensor_epoch",
        "host_sync_accuracy_verified": False,
        "raw_imu_period_ms": float(np.median(np.diff(imu_stamps))) / 1e6,
        "raw_cloud_period_ms": float(np.median(np.diff(cloud_stamps))) / 1e6,
    }
