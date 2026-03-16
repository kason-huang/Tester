# Simple Demo Viewer 实现逻辑分析

## 概述

`simple_demo_viewer.py` 是一个**交互式可视化界面**，用于实时控制和观察 habitat-sim 仿真环境。它通过 PyGame 提供用户界面，通过 Habitat-Sim 提供 3D 仿真能力。

## 核心架构

```
┌─────────────────────────────────────────────────────────┐
│                     应用主循环                           │
│  ┌──────────────┐    ┌──────────────┐    ┌────────────┐│
│  │  事件处理    │───→│  仿真更新    │───→│  渲染显示  ││
│  │ (PyGame)     │    │ (Habitat)    │    │ (PyGame)   ││
│  └──────────────┘    └──────────────┘    └────────────┘│
│         ↓                    ↑                    ↓      │
│    键盘输入          observations字典      显示到屏幕    │
└─────────────────────────────────────────────────────────┘
```

## 关键组件关系

### 1. **Habitat-Sim (仿真引擎)**

```python
# 职责：3D 场景渲染、物理仿真、传感器数据生成
sim = habitat_sim.Simulator(cfg)
observations = sim.step(action)  # 返回传感器数据
```

**Habitat-Sim 提供**：
- 3D 场景加载和渲染
- 物理引擎（碰撞检测）
- 传感器数据（RGB图像、深度图）
- 动作执行接口

### 2. **PyGame (显示层)**

```python
# 职责：窗口管理、用户输入、图像显示
pygame.init()
screen = pygame.display.set_mode((1024, 512))
```

**PyGame 提供**：
- 窗口创建和管理
- 键盘事件监听
- 2D 图像显示
- 文本叠加

## 数据流向

```
用户键盘输入 (PyGame)
    ↓
action = "move_forward"
    ↓
sim.step(action) ──→ [Habitat-Sim 3D引擎]
    ↓
observations = {
    "rgb": <512x512x4 RGBA图像>,
    "depth": <512x512 深度图>
}
    ↓
observations_to_image() ──→ [格式转换]
    ↓
frame = <512x1024x3 RGB图像> (并排显示)
    ↓
pygame.surfarray.make_surface() ──→ [PyGame显示]
    ↓
显示到屏幕
```

## 关键函数解析

### 1. **`observations_to_image()`** - 数据格式转换

```python
def observations_to_image(observations):
    """将 Habitat 传感器数据转换为可显示图像"""
    # 输入：Habitat 的 observations 字典
    # 处理：深度图归一化、RGBA→RGB转换、维度调整
    # 输出：水平拼接的RGB图像数组

    images = []
    for sensor_name in observations:
        obs = observations[sensor_name]

        # 深度图特殊处理（归一化到0-255）
        if obs.dtype == np.float32:
            obs = (obs - obs.min()) / (obs.max() - obs.min())
            obs = (obs * 255).astype(np.uint8)

        # RGBA → RGB
        if obs.shape[2] == 4:
            obs = obs[:, :, :3]

        images.append(obs)

    # 水平拼接所有传感器图像
    return np.concatenate(images, axis=1)
```

### 2. **`overlay_text()`** - 文本信息叠加

```python
def overlay_text(image, text_lines, font_size=0.5):
    """在图像上叠加文本信息（FPS、位置、控制说明等）"""
    # 1. 创建带 alpha 通道的表面
    surface = pygame.Surface((w, h), pygame.SRCALPHA)

    # 2. 渲染文本并添加半透明黑色背景
    for line in text_lines:
        text_surface = font.render(line, True, (255, 255, 255))
        bg_rect = text_surface.get_rect(topleft=(10, y))
        pygame.draw.rect(surface, (0, 0, 0, 180), bg_rect)

    # 3. Alpha 混合到原图像
    alpha = text_array[:, :, 3] / 255.0
    image[:, :, c] = (image[:, :, c] * (1 - alpha) +
                      text_array[:, :, c] * alpha)
```

### 3. **`InteractiveViewer`** - 主控制器

```python
class InteractiveViewer:
    def run(self):
        while self.running:
            # 1. 处理事件 (PyGame)
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False

            # 2. 获取输入并执行动作 (Habitat)
            keys = pygame.key.get_pressed()
            action = self.get_action_from_keys(keys)
            if action:
                observations = sim.step(action)  # Habitat仿真

            # 3. 渲染显示 (PyGame)
            frame = observations_to_image(observations)  # 转换数据
            surface = pygame.surfarray.make_surface(frame)  # 创建显示表面
            self.screen.blit(surface, (0, 0))
            pygame.display.update()
```

## 两者的分工

| 功能 | Habitat-Sim | PyGame |
|------|-------------|--------|
| **3D渲染** | ✅ GPU加速的3D场景 | ❌ 不处理3D |
| **物理仿真** | ✅ 碰撞检测、运动 | ❌ 无物理引擎 |
| **传感器数据** | ✅ RGB/深度图生成 | ❌ 不生成传感器数据 |
| **窗口显示** | ❌ 无窗口系统 | ✅ 创建窗口 |
| **用户输入** | ❌ 无输入处理 | ✅ 键盘/鼠标事件 |
| **2D显示** | ❌ 不显示到屏幕 | ✅ 图像显示 |

## 关键设计点

### 1. **初始化顺序**

```python
# 必须先初始化 PyGame，避免 OpenGL 上下文冲突
pygame.init()
sim = habitat_sim.Simulator(cfg)  # 后初始化 Habitat
```

**原因**：两个库都使用 OpenGL，先初始化 PyGame 可以避免上下文冲突。

### 2. **数据桥接**

```python
# Habitat 返回的是 numpy 数组
observations["rgb"]  # shape: (512, 512, 4) RGBA

# 转换为 PyGame 可用的格式
frame = np.transpose(frame, (1, 0, 2))  # 调整轴顺序
surface = pygame.surfarray.make_surface(frame)  # 创建表面
```

### 3. **异步更新**

```python
# 仿真和渲染分离
action = self.get_action_from_keys(keys)  # 读取输入
if action:
    observations = sim.step(action)       # 更新仿真
self.render()                             # 渲染当前状态
```

### 4. **动作空间配置**

```python
agent_cfg.action_space = {
    "move_forward": habitat_sim.agent.ActionSpec(
        "move_forward",
        habitat_sim.agent.ActuationSpec(amount=0.25)  # 每次前进0.25米
    ),
    "turn_left": habitat_sim.agent.ActionSpec(
        "turn_left",
        habitat_sim.agent.ActuationSpec(amount=15.0)  # 每次左转15度
    ),
    "turn_right": habitat_sim.agent.ActionSpec(
        "turn_right",
        habitat_sim.agent.ActuationSpec(amount=15.0)  # 每次右转15度
    ),
}
```

## 与 Headless 模式的对比

| 特性 | Headless 模式 | 交互式查看器 |
|------|--------------|-------------|
| **显示** | ❌ 保存到文件 | ✅ 实时显示 |
| **输入** | ❌ 预定义动作 | ✅ 键盘控制 |
| **PyGame** | ❌ 不需要 | ✅ 必须 |
| **用途** | 批量数据采集 | 交互式探索 |
| **性能** | 更快（无显示开销） | 稍慢（实时渲染） |
| **调试** | 需要查看文件 | 实时反馈 |

## 控制说明

### 键盘控制

| 按键 | 功能 | 动作 |
|------|------|------|
| **W** | 前进 | move_forward (0.25m) |
| **A** | 左转 | turn_left (15°) |
| **D** | 右转 | turn_right (15°) |
| **R** | 重置环境 | reset |
| **ESC** | 退出程序 | quit |

### 冷却机制

```python
self.action_cooldown = 0
self.action_delay = 5  # 帧数

# 防止按键重复触发
if self.action_cooldown > 0:
    self.action_cooldown -= 1
    return None
```

## 信息显示

### 实时统计信息

```python
info_lines = [
    f"FPS: {self.current_fps:.1f}",           # 帧率
    f"步数: {self.step_count}",                # 总步数
    f"位置: ({pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f})",  # 3D坐标
    "",
    "控制:",
    "W - 前进",
    "A/D - 左转/右转",
    "R - 重置环境",
    "ESC - 退出"
]
```

## 传感器配置

### RGB 传感器

```python
rgb_sensor_spec = habitat_sim.CameraSensorSpec()
rgb_sensor_spec.uuid = "rgb"
rgb_sensor_spec.sensor_type = habitat_sim.SensorType.COLOR
rgb_sensor_spec.resolution = [512, 512]
rgb_sensor_spec.position = [0.0, 1.5, 0.0]  # 1.5米高度
rgb_sensor_spec.hfov = 90.0  # 90度水平视野
```

### 深度传感器

```python
depth_sensor_spec = habitat_sim.CameraSensorSpec()
depth_sensor_spec.uuid = "depth"
depth_sensor_spec.sensor_type = habitat_sim.SensorType.DEPTH
depth_sensor_spec.resolution = [512, 512]
depth_sensor_spec.position = [0.0, 1.5, 0.0]
depth_sensor_spec.hfov = 90.0
```

## 性能优化

### FPS 控制

```python
self.target_fps = 60
self.clock.tick(self.target_fps)  # 限制帧率
```

### FPS 计算

```python
self.frame_count = 0
self.start_time = time.time()

elapsed = time.time() - self.start_time
if elapsed >= 1.0:
    self.current_fps = self.frame_count / elapsed
    self.frame_count = 0
    self.start_time = time.time()
```

## 依赖项

```
habitat-sim: 3D仿真引擎
pygame:      窗口和输入管理
numpy:       数据处理
```

## 总结

**Habitat-Sim** = 后端仿真引擎（3D世界、物理、传感器）
**PyGame** = 前端显示层（窗口、输入、2D渲染）

它们通过 `observations` 字典桥接：
- Habitat 生成数据 → PyGame 显示数据
- PyGame 接收输入 → Habitat 执行动作

这是一种经典的**前后端分离**架构，Habitat 专注于仿真逻辑，PyGame 专注于用户界面。这种设计使得：
1. 仿真逻辑可以独立于显示系统运行
2. 可以轻松切换不同的显示方式（PyGame、无头模式、Web界面等）
3. 便于测试和调试
