#!/usr/bin/env bash
# Build unmodified official Livox wire types only; never start a device driver.
set -euo pipefail
cd "$(dirname "$0")/.."
work="$PWD/.release-runtime"
test ! -e "$work"
mkdir -p "$work/src/livox_ros_driver2/msg"
python3 - "$work" <<'PY'
import hashlib
import pathlib
import sys
import urllib.request
root = pathlib.Path(sys.argv[1]) / 'src/livox_ros_driver2'
commit = '21445540f0d100dc86a7e6df312dd70bbdb4afdf'
digests = {'CustomMsg.msg': 'f42d6709db951b1fa307e929e742c0593cbf0d1b0ff977d2ed63ad8d7cee0a96',
           'CustomPoint.msg': 'b64b31a8edc8c8b3765d82b5d3ccd2d2e1f217b9525ef7007ab918674c619c59'}
for name, digest in digests.items():
    url = f'https://raw.githubusercontent.com/Livox-SDK/livox_ros_driver2/{commit}/msg/{name}'
    data = urllib.request.urlopen(url, timeout=30).read()
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError('Livox message digest mismatch: ' + name)
    (root / 'msg' / name).write_bytes(data)
(root / 'CMakeLists.txt').write_text('cmake_minimum_required(VERSION 3.16)\nproject(livox_ros_driver2)\nfind_package(ament_cmake REQUIRED)\nfind_package(rosidl_default_generators REQUIRED)\nfind_package(std_msgs REQUIRED)\nrosidl_generate_interfaces(${PROJECT_NAME} "msg/CustomPoint.msg" "msg/CustomMsg.msg" DEPENDENCIES std_msgs)\nament_export_dependencies(rosidl_default_runtime)\nament_package()\n')
(root / 'package.xml').write_text('<package format="3"><name>livox_ros_driver2</name><version>1.0.0</version><description>Unmodified Livox wire types for build-time validation; no driver.</description><maintainer email="development@example.invalid">Build validation</maintainer><license>MIT</license><buildtool_depend>ament_cmake</buildtool_depend><build_depend>rosidl_default_generators</build_depend><exec_depend>rosidl_default_runtime</exec_depend><depend>std_msgs</depend><member_of_group>rosidl_interface_packages</member_of_group><export><build_type>ament_cmake</build_type></export></package>')
PY
set +u
source /opt/ros/jazzy/setup.bash
set -u
cd "$work"
colcon build --merge-install --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3
