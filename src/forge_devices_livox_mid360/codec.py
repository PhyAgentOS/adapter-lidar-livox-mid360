"""Encode official Livox messages as existing Forge messages.

The live backend supplies ROS objects; codecs deliberately do not import ROS.
Point data is packed in one structured NumPy buffer. Only the ROS boundary
requires iterating the CustomPoint Python objects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
from forge_msgs import Imu, PointCloudBuffer
from forge_msgs.point_cloud_buffer import PointField

GRAVITY = 9.80665
POINT_DTYPE = np.dtype(
    [
        ("x", "<f4"),
        ("y", "<f4"),
        ("z", "<f4"),
        ("time_offset_ns", "<u4"),
        ("reflectivity", "u1"),
        ("line", "u1"),
        ("tag", "u1"),
    ]
)


@dataclass(frozen=True)
class SensorClock:
    """Explicit, shared clock mapping for point and IMU timestamps.

    ros_ns = device_ns + offset_ns. The offset is supplied by deployment after
    synchronization; no arrival-time estimate is made here.
    """

    domain: str
    mapping_id: str
    offset_ns: int

    def __post_init__(self) -> None:
        if not self.domain or not self.mapping_id:
            raise ValueError("clock domain and mapping_id are required")
        if isinstance(self.offset_ns, bool) or not isinstance(self.offset_ns, int):
            raise ValueError("clock offset must be an integer number of ns")

    def metadata(self, stamp_ns: int, frame_id: str, **extra: Any) -> dict:
        if not frame_id or not 0 <= stamp_ns < 2**63:
            raise ValueError("valid source timestamp and frame_id are required")
        if not 0 <= stamp_ns + self.offset_ns <= 2_147_483_647 * 10**9 + 999_999_999:
            raise ValueError("mapped timestamp is outside ROS2 Time range")
        return {
            "capture_timestamp_ns": stamp_ns,
            "frame_id": frame_id,
            "clock_domain": self.domain,
            "time_mapping_id": self.mapping_id,
            "ros_time_offset_ns": self.offset_ns,
            **extra,
        }


def encode_cloud(msg: Any, clock: SensorClock) -> tuple[PointCloudBuffer, dict]:
    if msg.point_num != len(msg.points):
        raise ValueError("CustomMsg point_num does not match points")
    if not 0 <= msg.lidar_id <= 255:
        raise ValueError("lidar_id must fit uint8")
    # Validate before casting: unsigned NumPy casts must not wrap invalid input.
    values = []
    for p in msg.points:
        if not 0 <= p.offset_time <= 2**32 - 1:
            raise ValueError("point time offset must fit uint32 ns")
        if any(not 0 <= v <= 255 for v in (p.reflectivity, p.line, p.tag)):
            raise ValueError("reflectivity/line/tag must fit uint8")
        values.append((p.x, p.y, p.z, p.offset_time, p.reflectivity, p.line, p.tag))
    points = np.array(values, dtype=POINT_DTYPE)
    if not np.isfinite(np.column_stack([points[k] for k in ("x", "y", "z")])).all():
        raise ValueError("non-finite Livox coordinates")
    # Preserve original sample order; FAST-LIO preprocessing uses point timing.
    fields = [
        PointField(
            name=name,
            offset=POINT_DTYPE.fields[name][1],
            datatype="float32"
            if name in ("x", "y", "z")
            else "uint32"
            if name == "time_offset_ns"
            else "uint8",
            count=1,
        )
        for name in POINT_DTYPE.names
    ]
    cloud = PointCloudBuffer(
        width=len(points),
        height=1,
        is_dense=True,
        byte_order="little_endian",
        point_stride=POINT_DTYPE.itemsize,
        row_stride=points.nbytes,
        fields=fields,
        data=points.tobytes(),
    )
    meta = clock.metadata(
        int(msg.timebase),
        msg.header.frame_id,
        lidar_id=int(msg.lidar_id),
        timestamp_source="livox_timebase",
    )
    header_ns = int(msg.header.stamp.sec) * 10**9 + int(msg.header.stamp.nanosec)
    if header_ns != int(msg.timebase):
        raise ValueError("CustomMsg header stamp differs from timebase; verify driver semantics")
    return cloud, meta


def encode_imu(
    msg: Any, clock: SensorClock, *, acceleration_unit: Literal["g", "m_s2"]
) -> tuple[Imu, dict]:
    """Raw Livox driver versions may publish g in a ROS Imu field: configure explicitly."""
    if acceleration_unit not in ("g", "m_s2"):
        raise ValueError("acceleration_unit must be g or m_s2")
    scale = GRAVITY if acceleration_unit == "g" else 1.0

    def vector(value: Any, factor: float = 1.0) -> dict:
        result = {k: float(getattr(value, k)) * factor for k in ("x", "y", "z")}
        if not all(np.isfinite(v) for v in result.values()):
            raise ValueError("non-finite IMU measurement")
        return result

    imu = Imu(
        orientation=None,
        angular_velocity=vector(msg.angular_velocity),
        linear_acceleration=vector(msg.linear_acceleration, scale),
    )
    stamp = int(msg.header.stamp.sec) * 10**9 + int(msg.header.stamp.nanosec)
    return imu, clock.metadata(stamp, msg.header.frame_id, timestamp_source="livox_imu_stamp")
