#!/usr/bin/env python3
"""
Habitat-Sim 语义场景对比工具
对比普通 GLB 和语义 GLB 的差异
"""

import habitat_sim
import numpy as np
import time
import os

try:
    import pygame
except ImportError:
    print("错误: 需要安装 PyGame")
    print("安装命令: pip install pygame==2.0.1")
    exit(1)


def load_semantic_labels(semantic_txt_path):
    """加载语义标签文件"""
    labels = {}

    if not os.path.exists(semantic_txt_path):
        print(f"警告: 语义标签文件不存在: {semantic_txt_path}")
        return labels

    with open(semantic_txt_path, 'r') as f:
        lines = f.readlines()

    # 跳过标题行
    for line in lines[1:]:
        parts = line.strip().split(',')
        if len(parts) >= 4:
            idx = parts[0]
            obj_id = parts[1]
            label_name = parts[2]
            region_id = parts[3]
            labels[obj_id] = {
                'index': idx,
                'label': label_name,
                'region': region_id
            }

    return labels


def semantic_to_colored(semantic_obs, labels=None):
    """将语义观测转换为彩色图像，使用标签信息优化颜色"""
    h, w = semantic_obs.shape

    # 如果有标签信息，创建基于类别的颜色映射
    if labels:
        unique_labels = set()
        for obj_id, info in labels.items():
            unique_labels.add(info['label'])

        label_to_color = {}
        colors = [
            (255, 0, 0), (0, 255, 0), (0, 0, 255),
            (255, 255, 0), (255, 0, 255), (0, 255, 255),
            (128, 0, 0), (0, 128, 0), (0, 0, 128),
            (128, 128, 0), (128, 0, 128), (0, 128, 128),
            (255, 128, 0), (255, 0, 128), (128, 255, 0),
        ]

        for i, label_name in enumerate(sorted(unique_labels)):
            label_to_color[label_name] = colors[i % len(colors)]

    # 创建彩色图像
    semantic_rgb = np.zeros((h, w, 3), dtype=np.uint8)

    # 使用简单的哈希颜色
    for i in range(3):
        channel = (semantic_obs * (i + 1) * 37) % 256
        semantic_rgb[:, :, i] = channel.astype(np.uint8)

    return semantic_rgb


def observations_to_image(observations, labels=None):
    """将观测字典转换为可显示图像"""
    images = []

    for sensor_name in observations:
        obs = observations[sensor_name]

        if not isinstance(obs, np.ndarray):
            continue

        if len(obs.shape) == 1:
            continue

        # 语义观测特殊处理
        if sensor_name == "semantic":
            obs = semantic_to_colored(obs, labels)
            images.append(obs)
            continue

        # 转换数据格式
        if obs.dtype != np.uint8:
            if obs.dtype == np.float32 or obs.dtype == np.float64:
                # 深度图处理
                if len(obs.shape) == 2:
                    obs = (obs - obs.min()) / (obs.max() - obs.min() + 1e-8)
                    obs = (obs * 255).astype(np.uint8)
                    obs = np.stack([obs, obs, obs], axis=2)
                else:
                    obs = (obs * 255).astype(np.uint8)
            else:
                obs = obs.astype(np.uint8)

        # 处理 RGBA -> RGB
        if len(obs.shape) == 3 and obs.shape[2] == 4:
            obs = obs[:, :, :3]

        # 处理单通道 -> RGB
        if len(obs.shape) == 2:
            obs = np.stack([obs, obs, obs], axis=2)
        elif len(obs.shape) == 3 and obs.shape[2] == 1:
            obs = np.concatenate([obs] * 3, axis=2)

        images.append(obs)

    if not images:
        raise ValueError("没有可用的视觉传感器观测")

    # 拼接所有图像
    return np.concatenate(images, axis=1)


def overlay_text(image, text_lines, font_size=0.5):
    """在图像上叠加文本信息"""
    h, w = image.shape[:2]

    surface = pygame.Surface((w, h), pygame.SRCALPHA)

    try:
        font = pygame.font.Font(None, int(24 * font_size))
    except:
        font = pygame.font.SysFont("Arial", int(24 * font_size))

    y = 10
    for line in text_lines:
        text_surface = font.render(line, True, (255, 255, 255))
        bg_rect = text_surface.get_rect(topleft=(10, y))
        bg_rect.inflate_ip(4, 4)
        pygame.draw.rect(surface, (0, 0, 0, 180), bg_rect)
        surface.blit(text_surface, (10, y))
        y += 25

    text_array = pygame.surfarray.array3d(surface)

    if text_array.shape[2] == 4:
        alpha = text_array[:, :, 3] / 255.0
        for c in range(min(3, image.shape[2])):
            image[:, :, c] = (
                image[:, :, c] * (1 - alpha) +
                text_array[:, :, c] * alpha
            ).astype(np.uint8)

    return image


class SemanticComparisonViewer:
    """语义场景对比查看器"""

    def __init__(self, normal_sim, semantic_sim, semantic_labels, window_size=(1536, 768)):
        self.normal_sim = normal_sim
        self.semantic_sim = semantic_sim
        self.semantic_labels = semantic_labels
        self.window_size = window_size
        self.running = True
        self.clock = pygame.time.Clock()
        self.target_fps = 30

        # 设置显示
        self.screen = pygame.display.set_mode(window_size)
        pygame.display.set_caption("Habitat-Sim 语义对比查看器")

        # 同步两个仿真器的初始状态
        self.normal_observations = self.normal_sim.reset()
        self.semantic_observations = self.semantic_sim.reset()

        # 统计信息
        self.step_count = 0
        self.frame_count = 0
        self.start_time = time.time()
        self.current_fps = 0

        # 控制状态
        self.action_cooldown = 0
        self.action_delay = 5

        # 显示模式
        self.display_mode = "side_by_side"  # side_by_side, normal_only, semantic_only
        self.sensor_mode = "semantic"  # rgb, depth, semantic

    def get_action_from_keys(self, keys):
        """根据键盘输入返回动作"""
        action = None

        if self.action_cooldown > 0:
            self.action_cooldown -= 1
            return None

        if keys[pygame.K_w]:
            action = "move_forward"
            self.action_cooldown = self.action_delay
        elif keys[pygame.K_a]:
            action = "turn_left"
            self.action_cooldown = self.action_delay
        elif keys[pygame.K_d]:
            action = "turn_right"
            self.action_cooldown = self.action_delay

        return action

    def sync_agent_state(self):
        """同步两个仿真器的agent状态"""
        normal_agent = self.normal_sim.get_agent(0)
        semantic_agent = self.semantic_sim.get_agent(0)

        # 同步位置和旋转
        semantic_agent.state.position = normal_agent.state.position
        semantic_agent.state.rotation = normal_agent.state.rotation

    def get_info_text(self):
        """生成信息文本"""
        pos = self.normal_sim.get_agent(0).state.position

        mode_text = {
            "side_by_side": "并排对比",
            "normal_only": "仅普通场景",
            "semantic_only": "仅语义场景"
        }

        sensor_text = {
            "rgb": "RGB",
            "depth": "深度",
            "semantic": "语义"
        }

        info_lines = [
            f"模式: {mode_text.get(self.display_mode, self.display_mode)} | 传感器: {sensor_text.get(self.sensor_mode, self.sensor_mode)}",
            f"FPS: {self.current_fps:.1f} | 步数: {self.step_count}",
            f"位置: ({pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f})",
            f"语义标签数: {len(self.semantic_labels)}",
            "",
            "控制:",
            "W/A/D - 移动/转向",
            "S - 切换传感器 (R/G/D)",
            "M - 切换显示模式",
            "R - 重置 | ESC - 退出"
        ]

        return info_lines

    def render(self):
        """渲染当前帧"""
        images = []

        # 根据显示模式渲染
        if self.display_mode == "side_by_side":
            # 普通场景
            normal_obs = {self.sensor_mode: self.normal_observations[self.sensor_mode]}
            normal_frame = observations_to_image(normal_obs, self.semantic_labels)
            normal_frame = overlay_text(normal_frame, ["普通 GLB"])

            # 语义场景
            semantic_obs = {self.sensor_mode: self.semantic_observations[self.sensor_mode]}
            semantic_frame = observations_to_image(semantic_obs, self.semantic_labels)
            semantic_frame = overlay_text(semantic_frame, ["语义 GLB"])

            # 水平拼接
            frame = np.concatenate([normal_frame, semantic_frame], axis=1)

        elif self.display_mode == "normal_only":
            obs = {self.sensor_mode: self.normal_observations[self.sensor_mode]}
            frame = observations_to_image(obs, self.semantic_labels)

        else:  # semantic_only
            obs = {self.sensor_mode: self.semantic_observations[self.sensor_mode]}
            frame = observations_to_image(obs, self.semantic_labels)

        # 添加信息文本
        info_lines = self.get_info_text()
        frame = overlay_text(frame, info_lines)

        # 转换并显示
        frame = np.transpose(frame, (1, 0, 2))
        surface = pygame.surfarray.make_surface(frame)

        if surface.get_size() != self.window_size:
            surface = pygame.transform.scale(surface, self.window_size)

        self.screen.blit(surface, (0, 0))
        pygame.display.update()

    def reset_environments(self):
        """重置环境"""
        self.normal_observations = self.normal_sim.reset()
        self.semantic_observations = self.semantic_sim.reset()
        self.step_count = 0
        print("环境已重置")

    def run(self):
        """主循环"""
        print("=" * 60)
        print("Habitat-Sim 语义场景对比查看器")
        print("=" * 60)
        print("控制说明:")
        print("  W/A/D - 移动/转向")
        print("  S     - 切换传感器类型 (RGB/深度/语义)")
        print("  M     - 切换显示模式 (并排/普通/语义)")
        print("  R     - 重置环境")
        print("  ESC   - 退出")
        print("=" * 60)
        print(f"已加载 {len(self.semantic_labels)} 个语义标签")

        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif event.key == pygame.K_r:
                        self.reset_environments()
                    elif event.key == pygame.K_m:
                        modes = ["side_by_side", "normal_only", "semantic_only"]
                        idx = modes.index(self.display_mode)
                        self.display_mode = modes[(idx + 1) % len(modes)]
                        print(f"显示模式: {self.display_mode}")
                    elif event.key == pygame.K_s:
                        sensors = ["rgb", "depth", "semantic"]
                        idx = sensors.index(self.sensor_mode)
                        self.sensor_mode = sensors[(idx + 1) % len(sensors)]
                        print(f"传感器: {self.sensor_mode}")

            # 获取键盘输入并执行动作
            keys = pygame.key.get_pressed()
            action = self.get_action_from_keys(keys)

            if action:
                # 在普通场景执行动作
                self.normal_observations = self.normal_sim.step(action)

                # 同步并更新语义场景
                self.sync_agent_state()
                self.semantic_observations = self.semantic_sim.step(action)

                self.step_count += 1

            # 更新FPS
            self.frame_count += 1
            elapsed = time.time() - self.start_time
            if elapsed >= 1.0:
                self.current_fps = self.frame_count / elapsed
                self.frame_count = 0
                self.start_time = time.time()

            # 渲染
            self.render()
            self.clock.tick(self.target_fps)

        print(f"\n会话结束! 总步数: {self.step_count}")


def create_simulator(scene_path, enable_semantic=True):
    """创建仿真器"""
    backend_cfg = habitat_sim.SimulatorConfiguration()
    backend_cfg.scene_id = scene_path
    backend_cfg.gpu_device_id = 0

    # RGB 传感器
    rgb_sensor_spec = habitat_sim.CameraSensorSpec()
    rgb_sensor_spec.uuid = "rgb"
    rgb_sensor_spec.sensor_type = habitat_sim.SensorType.COLOR
    rgb_sensor_spec.resolution = [512, 512]
    rgb_sensor_spec.position = [0.0, 1.5, 0.0]
    rgb_sensor_spec.hfov = 90.0

    # 深度传感器
    depth_sensor_spec = habitat_sim.CameraSensorSpec()
    depth_sensor_spec.uuid = "depth"
    depth_sensor_spec.sensor_type = habitat_sim.SensorType.DEPTH
    depth_sensor_spec.resolution = [512, 512]
    depth_sensor_spec.position = [0.0, 1.5, 0.0]
    depth_sensor_spec.hfov = 90.0

    # 语义传感器
    semantic_sensor_spec = habitat_sim.CameraSensorSpec()
    semantic_sensor_spec.uuid = "semantic"
    semantic_sensor_spec.sensor_type = habitat_sim.SensorType.SEMANTIC
    semantic_sensor_spec.resolution = [512, 512]
    semantic_sensor_spec.position = [0.0, 1.5, 0.0]
    semantic_sensor_spec.hfov = 90.0

    # Agent 配置
    agent_cfg = habitat_sim.AgentConfiguration()
    agent_cfg.sensor_specifications = [rgb_sensor_spec, depth_sensor_spec, semantic_sensor_spec]

    # 动作空间
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

    cfg = habitat_sim.Configuration(backend_cfg, [agent_cfg])
    return habitat_sim.Simulator(cfg)


def main():
    """主函数"""
    pygame.init()

    scene_base = "data/scene_datasets/hm3d/00020-XYyR54sxe6b"
    normal_glb = os.path.join(scene_base, "XYyR54sxe6b.basis.glb")
    semantic_glb = os.path.join(scene_base, "XYyR54sxe6b.semantic.glb")
    semantic_txt = os.path.join(scene_base, "XYyR54sxe6b.semantic.txt")

    print("=" * 60)
    print("正在加载场景...")
    print(f"普通场景: {normal_glb}")
    print(f"语义场景: {semantic_glb}")

    # 加载语义标签
    print("\n正在加载语义标签...")
    semantic_labels = load_semantic_labels(semantic_txt)
    print(f"✓ 加载了 {len(semantic_labels)} 个语义标签")

    # 显示一些标签示例
    if semantic_labels:
        print("\n语义标签示例:")
        for i, (obj_id, info) in enumerate(list(semantic_labels.items())[:10]):
            print(f"  {obj_id}: {info['label']} (区域 {info['region']})")

    # 创建仿真器
    print("\n正在创建仿真器...")
    normal_sim = create_simulator(normal_glb)
    print("✓ 普通场景仿真器已创建")

    semantic_sim = create_simulator(semantic_glb)
    print("✓ 语义场景仿真器已创建")

    # 创建查看器
    viewer = SemanticComparisonViewer(normal_sim, semantic_sim, semantic_labels)

    try:
        viewer.run()
    finally:
        normal_sim.close()
        semantic_sim.close()
        print("仿真器已关闭")
        pygame.quit()


if __name__ == "__main__":
    main()
