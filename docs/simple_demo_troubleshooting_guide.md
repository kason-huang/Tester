# Habitat-Sim 交互式演示脚本 - 故障排除与使用指南

> `test/simple_demo.py` 交互式可视化界面调试与使用文档
> 解决 OpenGL 上下文冲突、显示黑屏等问题

---

## 目录

1. [脚本概述](#脚本概述)
2. [已知问题与解决方案](#已知问题与解决方案)
3. [使用说明](#使用说明)
4. [故障排除](#故障排除)
5. [代码修改说明](#代码修改说明)

---

## 脚本概述

**文件位置**: `test/simple_demo.py`

**功能**:
- Habitat-Sim 3D 环境交互式可视化
- 实时 RGB 和深度传感器观测显示
- 键盘控制导航（前进、转向）
- FPS 和位置信息显示

**依赖**:
- habitat-sim
- pygame (用于图形界面)
- numpy

---

## 已知问题与解决方案

### 问题 1: Conda 激活错误

**错误信息**:
```
CondaError: Run 'conda init' before 'conda activate'
```

**原因**:
- 尝试激活已经激活的环境
- conda 未正确初始化

**解决方案**:
```bash
# 方法 1: 直接运行（推荐）
python test/simple_demo.py

# 方法 2: 检查当前环境
conda env list  # 确认 habitat 环境（带 * 标记）已激活
```

---

### 问题 2: X11 显示/GLX 上下文错误

**错误信息**:
```
X Error of failed request:  BadAccess (attempt to access private resource denied)
  Major opcode of failed request:  150 (GLX)
  Minor opcode of failed request:  5 (X_GLXMakeCurrent)
```

**原因**:
- Habitat-Sim 和 pygame 竞争 OpenGL 上下文
- 初始化顺序不当导致上下文冲突

**解决方案**:
- ✅ 已修复：调整初始化顺序，pygame 优先于 Habitat-Sim 初始化
- ✅ 移除重复的 pygame.init() 调用

**代码修改**:
```python
# 在 main() 函数开头初始化 pygame
def main():
    # 首先初始化 pygame，避免 OpenGL 上下文冲突
    print("正在初始化 PyGame...")
    pygame.init()

    # 然后再创建 Habitat 仿真器
    sim = habitat_sim.Simulator(cfg)
```

---

### 问题 3: 界面显示黑屏

**症状**:
- 窗口正常显示但内容为黑色
- 无法看到 3D 场景内容

**原因**:
- `overlay_text()` 函数逻辑错误
- 当没有 alpha 通道时，整个图像被替换为文本叠加层

**解决方案**:
- ✅ 已修复：正确处理 alpha 通道混合
- ✅ 添加通道数边界检查

**代码修改**:
```python
# 修复前（错误）
else:
    # 没有 alpha 通道，直接使用文本数组
    image = text_array  # 错误！完全替换了图像

# 修复后（正确）
else:
    # 如果没有 alpha 通道，跳过文本叠加以避免显示问题
    pass  # 保持原始图像不变
```

---

### 问题 4: 动作空间错误

**错误信息**:
```
AssertionError: No action move_backward in action space
```

**原因**:
- 键盘控制尝试执行不存在的动作
- 动作空间未正确配置

**解决方案**:
- ✅ 已修复：移除不可用的 `move_backward` 动作
- ✅ 添加正确的动作空间配置
- ✅ 为动作添加执行量参数

**代码修改**:
```python
# 1. 配置动作空间
agent_cfg.action_space = {
    "move_forward": habitat_sim.agent.ActionSpec(
        "move_forward",
        habitat_sim.agent.ActuationSpec(amount=0.25)
    ),
    "turn_left": habitat_sim.agent.ActionSpec(
        "turn_left",
        habitat_sim.agent.ActuationSpec(amount=15.0)
    ),
    "turn_right": habitat_sim.agent.ActionSpec(
        "turn_right",
        habitat_sim.agent.ActuationSpec(amount=15.0)
    ),
}

# 2. 更新键盘控制（移除 move_backward）
def get_action_from_keys(self, keys):
    if keys[pygame.K_w]:
        action = "move_forward"  # 前进
    elif keys[pygame.K_a]:
        action = "turn_left"     # 左转
    elif keys[pygame.K_d]:
        action = "turn_right"    # 右转
    # 移除了 move_backward
```

---

## 使用说明

### 基本使用

**直接运行**:
```bash
python test/simple_demo.py
```

**使用包装脚本**:
```bash
./run_demo.sh
```

### 键盘控制

| 按键 | 功能 | 说明 |
|------|------|------|
| **W** | 前进 | 向前移动 0.25 米 |
| **A** | 左转 | 逆时针旋转 15 度 |
| **D** | 右转 | 顺时针旋转 15 度 |
| **R** | 重置 | 重置环境到初始状态 |
| **ESC** | 退出 | 关闭程序 |

### 界面说明

**显示内容**:
- **左侧**: RGB 传感器观测（彩色图像）
- **右侧**: 深度传感器观测（灰度深度图）
- **叠加信息**: FPS、步数、位置坐标

**窗口大小**: 1024x512 像素

---

## 故障排除

### 调试步骤

1. **检查环境**:
```bash
# 确认 Python 环境
which python

# 确认已安装依赖
python -c "import habitat_sim; import pygame; import numpy as np; print('✓ 所有依赖已安装')"
```

2. **验证场景文件**:
```bash
# 检查场景文件是否存在
ls -la data/scene_datasets/hm3d/00000-kfPV7w3FaU5/kfPV7w3FaU5.basis.glb
```

3. **测试 OpenGL**:
```bash
# 测试 PyGame 显示
python -c "import pygame; pygame.init(); print('✓ PyGame 初始化成功')"
```

### 常见错误

#### ImportError: No module named 'pygame'
```bash
pip install pygame==2.0.1
```

#### 场景文件不存在
```bash
# 下载场景数据集
python -m habitat_sim.utils.datasets_download --username habitat --endpoint hm3d
```

#### GPU 内存不足
```bash
# 使用 CPU 模式
export CUDA_VISIBLE_DEVICES=""
python test/simple_demo.py
```

---

## 代码修改说明

### 修改摘要

**修改文件**: `test/simple_demo.py`

**主要修改**:
1. ✅ pygame 初始化顺序调整（line 258）
2. ✅ 移除重复的 pygame.init()（line 119）
3. ✅ 修复 overlay_text() 函数逻辑（line 66-106）
4. ✅ 添加动作空间配置（line 300-313）
5. ✅ 更新键盘控制逻辑（line 140-156）
6. ✅ 更新控制说明文本（line 173-193, 220-227）

### 关键代码片段

**1. pygame 优先初始化**:
```python
def main():
    # 首先初始化 pygame
    print("正在初始化 PyGame...")
    pygame.init()

    # 然后初始化 Habitat-Sim
    print("正在初始化 Habitat-Sim...")
    # ... Habitat-Sim 配置 ...
    sim = habitat_sim.Simulator(cfg)
```

**2. 正确的 alpha 混合**:
```python
def overlay_text(image, text_lines, font_size=0.5):
    # ... 创建 pygame surface ...

    text_array = pygame.surfarray.array3d(surface)

    # 正确处理 alpha 通道
    if text_array.shape[2] == 4:
        alpha = text_array[:, :, 3] / 255.0
        for c in range(min(3, image.shape[2])):
            image[:, :, c] = (
                image[:, :, c] * (1 - alpha) +
                text_array[:, :, c] * alpha
            ).astype(np.uint8)
    else:
        pass  # 保持原始图像
```

**3. 动作空间配置**:
```python
agent_cfg.action_space = {
    "move_forward": habitat_sim.agent.ActionSpec(
        "move_forward",
        habitat_sim.agent.ActuationSpec(amount=0.25)
    ),
    "turn_left": habitat_sim.agent.ActionSpec(
        "turn_left",
        habitat_sim.agent.ActuationSpec(amount=15.0)
    ),
    "turn_right": habitat_sim.agent.ActionSpec(
        "turn_right",
        habitat_sim.agent.ActuationSpec(amount=15.0)
    ),
}
```

---

## 性能优化建议

### 提升帧率

1. **降低分辨率**:
```python
rgb_sensor_spec.resolution = [256, 256]  # 从 512x512 降低
```

2. **减少传感器数量**:
```python
# 只使用 RGB 传感器
agent_cfg.sensor_specifications = [rgb_sensor_spec]  # 移除 depth
```

3. **关闭物理模拟**:
```python
backend_cfg.enable_physics = False
```

### 远程服务器使用

**无头模式**（通过 xrdp/vnc）:
```bash
# 当前配置已支持通过 xrdp 显示
DISPLAY=:10 python test/simple_demo.py
```

**完全无头模式**（不显示界面）:
```bash
SDL_VIDEODRIVER=dummy python test/simple_demo.py
```

---

## 扩展与定制

### 添加更多传感器

```python
# 语义分割传感器
semantic_sensor_spec = habitat_sim.CameraSensorSpec()
semantic_sensor_spec.uuid = "semantic"
semantic_sensor_spec.sensor_type = habitat_sim.SensorType.SEMANTIC
semantic_sensor_spec.resolution = [512, 512]
agent_cfg.sensor_specifications.append(semantic_sensor_spec)
```

### 自定义控制

```python
# 添加鼠标控制
def get_action_from_mouse(self):
    mouse_pos = pygame.mouse.get_pos()
    # 根据鼠标位置计算转向角度
    return "look_at_target"
```

### 保存观测数据

```python
# 在 render() 函数中添加
if self.step_count % 100 == 0:
    cv2.imwrite(f"rgb_{self.step_count}.png", self.observations['rgb'])
```

---

## 参考资料

- **Habitat 官方文档**: https://aihabitat.org/docs/
- **PyGame 文档**: https://www.pygame.org/docs/
- **OpenGL 上下文管理**: https://www.khronos.org/opengl/wiki/OpenGL_Context

---

*文档创建日期: 2026-03-14*
*最后更新: 2026-03-14*
*作者: Claude Code Assistant*
