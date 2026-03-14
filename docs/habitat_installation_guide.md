# Habitat 安装与配置指南

> AI2 Habitat / Facebook Habitat - 具身智能仿真平台
> 适用于导航与探索、视觉语言导航 (VLN) 任务

---

## 目录

1. [系统要求](#系统要求)
2. [环境安装](#环境安装)
3. [验证安装](#验证安装)
4. [常见问题](#常见问题)
5. [快速开始示例](#快速开始示例)

---

## 系统要求

### 最低配置
- **操作系统**: Linux (Ubuntu 18.04+) 或 macOS
- **Python**: 3.7 - 3.10
- **内存**: 8GB+ RAM
- **存储**: 10GB+ 可用空间

### 推荐配置
- **GPU**: NVIDIA GPU with CUDA support (用于加速)
- **内存**: 16GB+ RAM
- **存储**: 50GB+ SSD (用于存储场景数据集)

---

## 环境安装

### 步骤 1: 创建 Conda 环境

```bash
conda create -n habitat python=3.9 -y
conda activate habitat
```

### 步骤 2: 安装依赖

```bash
# 基础依赖
conda install cmake vs2019_win-64 -c conda-forge  # Windows
conda install cmake -c conda-forge                 # Linux/macOS

# 安装 Habitat-Sim (仿真引擎)
pip install habitat-sim

# 安装 Habitat-Lab (任务定义与训练)
pip install habitat-lab
```

### 步骤 3: GPU 加速支持 (可选)

**带图形界面版本 (推荐):**
```bash
# 安装指定版本，带图形界面和物理引擎
conda install habitat-sim==0.2.4 withbullet -c conda-forge -c aihabitat

git clone --branch v0.2.4 https://github.com/facebookresearch/habitat-lab.git
cd habitat-lab
pip install -e habitat-lab  # install habitat_lab
pip install -e habitat-baselines # install habitat_baselines
```

**Headless 版本 (无图形界面，适用于服务器):**
```bash
# 无头模式，不显示图形界面
conda install habitat-sim==0.2.4 withbullet headless -c conda-forge -c aihabitat
```

**CPU-only 版本:**
```bash
pip install habitat-sim --no-binary habitat-sim
```

**说明：**
- `withbullet`: 启用 Bullet 物理引擎
- `headless`: 无头模式（不显示图形界面），去掉此参数即可启用可视化
- `==0.2.4`: 指定版本号

---

## 验证安装

### 测试 1: 基础导入测试

创建测试文件 `test_habitat.py`:

```python
import habitat
import habitat_sim

print("✓ Habitat 版本:", habitat.__version__)
print("✓ Habitat-Sim 版本:", habitat_sim.__version__)
```

运行测试:
```bash
python test_habitat.py
```

### 测试 2: 运行简单仿真

```python
import habitat_sim

# 创建仿真配置
sim_settings = {
    "scene_id": "./data/scene_datasets/habitat-test-scenes/van-gogh-room.glb",
    "sensor_height": 1.5,
    "sensor_pitch": 0,
    "hfov": "90",
    "enable_glfw": True,
}

# 创建仿真器
cfg = habitat_sim.SimulatorConfiguration()
cfg.scene_id = sim_settings["scene_id"]
cfg.gpu_device_id = 0

sim = habitat_sim.Simulator(cfg)

# 获取初始观测
observations = sim.reset()
print("✓ 仿真器运行成功!")
print(f"RGB 观测形状: {observations['rgb'].shape}")

sim.close()
```

### 测试 3: 运行官方示例

```bash
# 下载测试场景
python -m habitat_sim.utils.datasets_download --username habitat --endpoint habitat-test-scenes

# 运行示例
python examples/habitat_sim.py
```

---

## 常见问题

### Q1: ImportError: No module named 'habitat'

**解决方案:**
```bash
# 确认环境已激活
conda activate habitat

# 重新安装
pip install --upgrade habitat-sim habitat-lab
```

### Q2: OpenGL/GPU 相关错误

**解决方案:**
```bash
# Linux: 安装 NVIDIA 驱动
sudo apt-get update
sudo apt-get install nvidia-driver-515

# 或使用 CPU 版本
export HABITAT_SIM_GPU=False
```

### Q3: 缺少场景数据集

**解决方案:**
```bash
# 下载 Gibson 数据集
python -m habitat_sim.utils.datasets_download --username habitat --endpoint gibson

# 下载 Matterport3D 数据集（需申请权限）
# 访问: https://niessner.github.io/Matterport/
```

---

## 快速开始示例

### 示例 1: 基础导航任务

```python
import habitat
from habitat.config.default import get_config

# 加载 PointNav 任务配置
config = get_config("configs/tasks/pointnav.yaml")

# 修改配置为 CPU 模式（如无 GPU）
config.habitat.simulator.habitat_sim_v0.gpu_device_id = -1

# 创建环境
env = habitat.Env(config=config)

# 运行一个 episode
observations = env.reset()
print(f"观测键: {observations.keys()}")

# 随机动作
for _ in range(10):
    action = env.action_space.sample()
    observations = env.step(action)
    print(f"动作: {action}, 奖励: {observations['reward']}")

env.close()
```

### 示例 2: 可视化智能体视角

```python
import habitat
import cv2
from habitat.config.default import get_config

config = get_config("configs/tasks/pointnav.yaml")
env = habitat.Env(config=config)

observations = env.reset()

# 保存 RGB 图像
rgb = observations["rgb"]
cv2.imwrite("habitat_view.png", rgb[:, :, ::-1])  # RGB -> BGR

print("✓ 图像已保存到 habitat_view.png")

env.close()
```

---

## 下一步

1. **深入学习**: 查看 [Habitat 官方文档](https://aihabitat.org/docs/)
2. **训练模型**: 尝试训练 PPO/DQN 策略
3. **VLN 任务**: 集成视觉语言导航数据集
4. **自定义任务**: 修改环境、传感器和奖励函数

---

## 参考资源

- **GitHub**: https://github.com/facebookresearch/habitat
- **官方文档**: https://aihabitat.org/docs/
- **论文**: "Habitat: A Platform for Embodied AI Research" (CVPR 2019)
- **论坛**: https://github.com/facebookresearch/habitat/discussions

---

*文档创建日期: 2026-03-13*
