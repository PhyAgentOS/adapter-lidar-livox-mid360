# 接口

输入：tick、finish。输出：point_cloud（PointCloudBuffer）、imu（Imu）、status（PolicyCommandStatus）。

ROS2 的 LaserScan、Odometry、OccupancyGrid、Path、TF 在后端交换，不新增 Forge 消息类型。具体配置键见示例 YAML；topic、ROS domain、程序路径由调用方指定。
