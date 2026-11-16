"""Optional ownership of an official Livox driver; no robot-specific defaults."""

import json
import os
from contextlib import contextmanager
from pathlib import Path

from .clock_probe import scout
from .process import OwnedProcess


def driver_command(config):
    cfg = config["managed_driver"]
    folder = Path(cfg["session_dir"])
    folder.mkdir(parents=True, exist_ok=True)
    network = json.loads(Path(cfg["network_config"]).read_text())
    for key in ("cmd_data_ip", "push_msg_ip", "point_data_ip", "imu_data_ip"):
        network["MID360"]["host_net_info"][key] = cfg["host_ip"]
    network["lidar_configs"][0]["ip"] = cfg["lidar_ip"]
    target = folder / "livox_network.json"
    target.write_text(json.dumps(network))
    params = {
        "xfer_format": 1,
        "multi_topic": 0,
        "data_src": 0,
        "publish_freq": cfg.get("publish_hz", 10.0),
        "output_data_type": 0,
        "frame_id": cfg.get("frame_id", "livox_frame"),
        "user_config_path": str(target),
    }
    args = [cfg["executable"], "--ros-args"]
    for key, value in params.items():
        args += ["-p", f"{key}:={value}"]
    return args + [
        "-r",
        "livox/lidar:=" + config["cloud_topic"],
        "-r",
        "livox/imu:=" + config["imu_topic"],
    ]


@contextmanager
def capture(config):
    if not config.get("managed_driver"):
        yield config
        return
    cfg = config["managed_driver"]
    folder = Path(cfg["session_dir"])
    process = OwnedProcess()
    try:
        argv = driver_command(config)
        process.start(
            argv,
            cwd=folder,
            log_path=folder / "livox.log",
            env={**os.environ, "ROS_DOMAIN_ID": str(config["ros_domain_id"])},
        )
        clock = scout(
            config["ros_domain_id"],
            config["cloud_topic"],
            config["imu_topic"],
            folder / "livox.log",
            config["imu_acceleration_unit"],
        )
        clock["mapping_id"] = cfg["time_mapping_id"]
        (folder / "sensor_clock.json").write_text(json.dumps(clock))
        yield {
            **config,
            "clock_confirmed": True,
            "clock": {k: clock[k] for k in ("domain", "mapping_id", "offset_ns")},
            "_owned_driver": process,
        }
    finally:
        process.stop()
