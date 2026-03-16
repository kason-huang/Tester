#!/usr/bin/env python3
"""
Habitat-Sim 交互式可视化界面
支持实时 RGB/深度观测显示和键盘控制
"""

import habitat_sim
import numpy as np
import time

try:
    import pygame
except ImportError:
    print("错误: 需要安装 PyGame")
    print("安装命令: pip install pygame==2.0.1")
    exit(1)


def observations_to_image(observations):
    """将观测字典转换为可显示图像"""
    images = []

    for sensor_name in observations:
        obs = observations[sensor_name]

        if not isinstance(obs, np.ndarray):
            continue

        if len(obs.shape) == 1:
            continue

        # 转换数据格式
        if obs.dtype != np.uint8:
            if obs.dtype == np.float32 or obs.dtype == np.float64:
                # 深度图处理
                if len(obs.shape) == 2:
                    # 归一化深度图到 0-255
                    obs = (obs - obs.min()) / (obs.max() - obs.min() + 1e-8)
                    obs = (obs * 255).astype(np.uint8)
                    # 转换为 RGB
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

    # 确保使用 SRCALPHA 标志创建带 alpha 通道的表面
    surface = pygame.Surface((w, h), pygame.SRCALPHA)

    # 加载字体
    try:
        font = pygame.font.Font(None, int(24 * font_size))
    except:
        font = pygame.font.SysFont("Arial", int(24 * font_size))

    y = 10
    for line in text_lines:
        text_surface = font.render(line, True, (255, 255, 255))
        # 添加黑色背景
        bg_rect = text_surface.get_rect(topleft=(10, y))
        bg_rect.inflate_ip(4, 4)
        pygame.draw.rect(surface, (0, 0, 0, 180), bg_rect)
        surface.blit(text_surface, (10, y))
        y += 25

    # 转换回 numpy 并叠加
    text_array = pygame.surfarray.array3d(surface)

    # 确保 text_array 有 alpha 通道（因为使用了 SRCALPHA）
    if text_array.shape[2] == 4:
        # Alpha 混合
        alpha = text_array[:, :, 3] / 255.0
        for c in range(min(3, image.shape[2])):
            image[:, :, c] = (
                image[:, :, c] * (1 - alpha) +
                text_array[:, :, c] * alpha
            ).astype(np.uint8)
    else:
        # 如果没有 alpha 通道，跳过文本叠加以避免显示问题
        pass

    return image


class InteractiveViewer:
    """交互式可视化查看器"""

    def __init__(self, sim, window_size=(1024, 512)):  # 2个传感器，调整宽度
        self.sim = sim
        self.window_size = window_size
        self.running = True
        self.clock = pygame.time.Clock()
        self.target_fps = 60

        # 设置显示模式（pygame 已经在 main 中初始化）
        self.screen = pygame.display.set_mode(window_size)
        pygame.display.set_caption("Habitat-Sim Semantic GLB 查看器 (RGB = 语义)")

        # 获取初始观测
        self.observations = self.sim.reset()

        # 🔍 调试：打印观测数据结构
        print("\n" + "="*50)
        print("观测数据调试信息：")
        print("="*50)
        for key, value in self.observations.items():
            if isinstance(value, np.ndarray):
                print(f"  {key}:")
                print(f"    形状: {value.shape}")
                print(f"    数据类型: {value.dtype}")
                print(f"    值范围: [{value.min():.2f}, {value.max():.2f}]")
        print("="*50 + "\n")

        # FPS 计算
        self.frame_count = 0
        self.start_time = time.time()
        self.current_fps = 0

        # 控制状态
        self.action_cooldown = 0
        self.action_delay = 5  # 帧数

        # 统计信息
        self.step_count = 0
        self.agent_position = self.sim.get_agent(0).state.position
        self.agent_rotation = self.sim.get_agent(0).state.rotation

        # 显示模式控制
        self.display_mode = "all"  # all, rgb, depth, semantic
        self.available_modes = ["all", "rgb", "depth", "semantic"]

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

    def update_info(self):
        """更新统计信息"""
        self.step_count += 1
        agent = self.sim.get_agent(0)
        self.agent_position = agent.state.position
        self.agent_rotation = agent.state.rotation

        # 计算 FPS
        self.frame_count += 1
        elapsed = time.time() - self.start_time
        if elapsed >= 1.0:
            self.current_fps = self.frame_count / elapsed
            self.frame_count = 0
            self.start_time = time.time()

    def get_info_text(self):
        """生成信息文本"""
        pos = self.agent_position
        rot = self.agent_rotation

        # 显示模式指示
        mode_text = {
            "all": "全部 (RGB + 深度)",
            "rgb": "仅 RGB",
            "depth": "仅深度",
            "semantic": "语义 (与RGB相同)"
        }

        info_lines = [
            f"显示模式: {mode_text.get(self.display_mode, self.display_mode)}",
            f"FPS: {self.current_fps:.1f}",
            f"步数: {self.step_count}",
            f"位置: ({pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f})",
            "",
            "[提示] semantic.glb 的 RGB 就是语义可视化",
            "",
            "控制:",
            "W - 前进",
            "A/D - 左转/右转",
            "1/2/3/4 - 切换显示模式",
            "   1=全部 2=RGB 3=深度 4=语义",
            "R - 重置环境",
            "ESC - 退出"
        ]

        return info_lines

    def filter_observations(self, mode):
        """根据显示模式过滤观测数据"""
        if mode == "all":
            return self.observations
        elif mode == "rgb":
            if "rgb" in self.observations:
                return {"rgb": self.observations["rgb"]}
            return {}
        elif mode == "depth":
            if "depth" in self.observations:
                return {"depth": self.observations["depth"]}
            return {}
        elif mode == "semantic":
            # semantic.glb 的 RGB 传感器本身就是语义可视化
            if "rgb" in self.observations:
                return {"semantic": self.observations["rgb"]}
            return {}

        return self.observations

    def render(self):
        """渲染当前帧"""
        # 根据显示模式过滤观测
        filtered_obs = self.filter_observations(self.display_mode)

        # 转换观测为图像
        frame = observations_to_image(filtered_obs)

        # 叠加信息文本
        info_lines = self.get_info_text()
        frame = overlay_text(frame, info_lines)

        # 转换为 PyGame 表面并显示
        frame = np.transpose(frame, (1, 0, 2))
        surface = pygame.surfarray.make_surface(frame)

        # 缩放到窗口大小
        if surface.get_size() != self.window_size:
            surface = pygame.transform.scale(surface, self.window_size)

        self.screen.blit(surface, (0, 0))
        pygame.display.update()

    def reset_environment(self):
        """重置环境"""
        self.observations = self.sim.reset()
        self.step_count = 0
        print("环境已重置")

    def run(self):
        """主循环"""
        print("=" * 50)
        print("Habitat-Sim 交互式查看器")
        print("=" * 50)
        print("控制说明:")
        print("  W     - 前进")
        print("  A/D   - 左转/右转")
        print("  1/2/3/4 - 切换显示模式")
        print("          1=全部 2=RGB(语义) 3=深度 4=语义")
        print("  R     - 重置环境")
        print("  ESC   - 退出")
        print("=" * 50)
        print("\n[TIPS] 使用 semantic.glb 时，RGB 显示的就是语义分割图")

        while self.running:
            # 处理事件
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif event.key == pygame.K_r:
                        self.reset_environment()
                    elif event.key == pygame.K_1:
                        self.display_mode = "all"
                    elif event.key == pygame.K_2:
                        self.display_mode = "rgb"
                    elif event.key == pygame.K_3:
                        self.display_mode = "depth"
                    elif event.key == pygame.K_4:
                        self.display_mode = "semantic"

            # 获取键盘输入并执行动作
            keys = pygame.key.get_pressed()
            action = self.get_action_from_keys(keys)

            if action:
                # 执行动作
                self.observations = self.sim.step(action)
                self.update_info()

            # 渲染
            self.render()

            # 控制 FPS
            self.clock.tick(self.target_fps)

        print(f"\n会话结束! 总步数: {self.step_count}")


def main():
    """主函数"""
    # 首先初始化 pygame，避免 OpenGL 上下文冲突
    print("正在初始化 PyGame...")
    pygame.init()

    # 创建仿真配置
    sim_settings = {
        # "scene_id": "data/scene_datasets/hm3d/00000-kfPV7w3FaU5/kfPV7w3FaU5.basis.glb",
        "scene_id": "data/scene_datasets/hm3d/00020-XYyR54sxe6b/XYyR54sxe6b.semantic.glb",
        "sensor_height": 1.5,
        "sensor_pitch": 0,
        "hfov": "90",
    }

    print("正在初始化 Habitat-Sim...")

    # 创建仿真器配置
    backend_cfg = habitat_sim.SimulatorConfiguration()
    backend_cfg.scene_id = sim_settings["scene_id"]
    backend_cfg.gpu_device_id = 0

    # 创建 RGB 传感器
    rgb_sensor_spec = habitat_sim.CameraSensorSpec()
    rgb_sensor_spec.uuid = "rgb"
    rgb_sensor_spec.sensor_type = habitat_sim.SensorType.COLOR
    rgb_sensor_spec.resolution = [512, 512]
    rgb_sensor_spec.position = [0.0, sim_settings["sensor_height"], 0.0]
    rgb_sensor_spec.hfov = float(sim_settings["hfov"])

    # 创建深度传感器
    depth_sensor_spec = habitat_sim.CameraSensorSpec()
    depth_sensor_spec.uuid = "depth"
    depth_sensor_spec.sensor_type = habitat_sim.SensorType.DEPTH
    depth_sensor_spec.resolution = [512, 512]
    depth_sensor_spec.position = [0.0, sim_settings["sensor_height"], 0.0]
    depth_sensor_spec.hfov = float(sim_settings["hfov"])

    # 创建 agent 配置
    # 注意：semantic.glb 不需要额外的 semantic 传感器
    # RGB 传感器本身就会显示语义分割可视化
    agent_cfg = habitat_sim.AgentConfiguration()
    agent_cfg.sensor_specifications = [rgb_sensor_spec, depth_sensor_spec]

    # 设置动作空间
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

    # 创建完整配置
    cfg = habitat_sim.Configuration(backend_cfg, [agent_cfg])

    # 创建仿真器
    sim = habitat_sim.Simulator(cfg)

    print("[OK] 仿真器初始化成功!")
    print(f"场景: {sim_settings['scene_id']}")

    # 检测是否是 semantic.glb
    if "semantic.glb" in sim_settings['scene_id']:
        print("\n" + "="*50)
        print("[INFO] 使用语义场景文件 (semantic.glb)")
        print("="*50)
        print("在这个场景中：")
        print("  - RGB 传感器显示的就是语义分割可视化")
        print("  - 不同颜色代表不同的物体类别")
        print("  - 模式2 (RGB) 和模式4 (语义) 显示相同内容")
        print("="*50 + "\n")

    print(f"传感器: RGB (512x512), Depth (512x512)")
    print("注意: semantic.glb 中 RGB 显示的就是语义分割可视化")
    print("\n提示: 使用 1/2/3/4 键切换显示模式")

    # 创建并运行查看器
    viewer = InteractiveViewer(sim)

    try:
        viewer.run()
    finally:
        sim.close()
        print("仿真器已关闭")
        pygame.quit()


if __name__ == "__main__":
    main()
