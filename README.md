# Mid-360 采集

接收 Livox 点云与 IMU，发布 Forge PointCloudBuffer 和 Imu，保留逐点时间、线号、反射率和采样上下文。

## 运行要求

- Node 版本：`0.2.0`；兼容 **Forge 1**。
- Linux x86_64、Ubuntu 24.04、Python 3.12 ABI、ROS 2 Jazzy。
- Dora CLI / Python 绑定 `0.4.1`、Forge Msgs `1.3.0`、Forge Common `1.0.1`。
- ROS 2、算法后端、Livox 消息工作空间由部署方提供，不包含在 Node 包内。启动前加载对应 ROS setup，运行 `--check-runtime` 检查环境；该命令不连接硬件。

制品是 `directory_tar_gz`，解压后保留整个 `livox_mid360/` 目录，入口为 `livox_mid360/livox_mid360`。冻结包包含 Dora Python 绑定，不能只升级外部 Dora CLI 来切换到 Forge 2。

## 能力边界与可选配置

- 默认订阅外部 Livox 驱动；配置 `managed_driver` 后可托管独立驱动进程。网络地址、配置文件、时钟映射和输出话题由调用方提供。
- 托管模式只修改会话目录中的网络配置副本，不修改原始配置。仅停止自己启动的进程。
- 托管模式依赖驱动的 `FORGE_SENSOR_CLOCK` 诊断；不带此诊断的普通驱动应使用外部管理模式，并按接口提供已核对的时钟信息。不会猜测传感器时钟或宣称具有 PTP 精度。

这些能力通过配置启用，未配置的可选功能保持关闭。Node 仅拥有自己的后端子进程，不接管其他应用进程或写入机器人厂家工程。快照是运行观测，不是控制接口；读取方负责检查时效。

## 开发与构建

```bash
uv sync --group dev
uv run livox_mid360 --check-config --config config/sensor.example.yaml
uv run pytest
uv run ruff check .
uv pip install --python .venv/bin/python -r requirements-build.txt
source /opt/ros/jazzy/setup.bash
# 按部署环境加载所需消息及算法工作空间。
BUILD_PYTHON=.venv/bin/python bash scripts/build_pyinstaller.sh
```

配置示例中的路径和话题需由使用者填入；实际执行应由 Dora dataflow 编排。构建时使用与测试相同的依赖环境。`--version`、配置检查和单元测试不替代 ROS 后端及真机验收。

接口说明见 [docs/interfaces.md](docs/interfaces.md)，配置在 `config/`，实现位于 `src/`，测试位于 `tests/`。构建工具、测试及源码不随冻结运行制品提供。
