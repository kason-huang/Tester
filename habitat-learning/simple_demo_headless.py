import habitat_sim
import numpy as np
import random
import os
from PIL import Image

# 创建输出目录
output_dir = "headless_output"
os.makedirs(output_dir, exist_ok=True)

# 创建仿真配置
sim_settings = {
    "scene_id": "data/scene_datasets/hm3d/00000-kfPV7w3FaU5/kfPV7w3FaU5.basis.glb",
    "sensor_height": 1.5,
    "sensor_pitch": 0,
    "hfov": "90",
    "enable_glfw": False,  # 关键：禁用显示窗口以启用 headless 模式
}

# 创建仿真器配置
backend_cfg = habitat_sim.SimulatorConfiguration()
backend_cfg.scene_id = sim_settings["scene_id"]
backend_cfg.gpu_device_id = 0
# 注意: enable_glfw 需要通过其他方式配置（环境变量或配置文件）

# 创建 agent 配置
# 定义 RGB 传感器 - 使用 CameraSensorSpec
rgb_sensor_spec = habitat_sim.CameraSensorSpec()
rgb_sensor_spec.uuid = "rgb"
rgb_sensor_spec.sensor_type = habitat_sim.SensorType.COLOR
rgb_sensor_spec.resolution = [512, 512]
rgb_sensor_spec.position = [0.0, sim_settings["sensor_height"], 0.0]

agent_cfg = habitat_sim.AgentConfiguration()
agent_cfg.sensor_specifications = [rgb_sensor_spec]

# 创建完整配置
cfg = habitat_sim.Configuration(backend_cfg, [agent_cfg])

sim = habitat_sim.Simulator(cfg)

# 获取初始观测
observations = sim.reset()
print("✓ 仿真器初始化成功（headless 模式）")
print(f"可用的观测键: {list(observations.keys())}")

# 定义可用动作（只使用实际存在的动作）
actions = ["move_forward", "turn_left", "turn_right"]

# 保存初始观测
def save_observation(rgb_data, step_id, suffix="before"):
    """保存 RGB 观测图片"""
    # 转换 RGBA 到 RGB（移除 alpha 通道）
    rgb_rgb = rgb_data[:, :, :3]
    # 保存为 PNG
    img = Image.fromarray(rgb_rgb)
    filename = f"{output_dir}/step_{step_id:03d}_{suffix}.png"
    img.save(filename)
    return filename

# 随机运动并保存图片（每个保存点执行多个动作以获得更大运动幅度）
print("\n开始随机运动...")

# 设置每个保存点之间的动作数量
actions_per_save = 20  # 每次保存前执行20个动作（更大的运动幅度）
total_saves = 5        # 总共保存5次

for save_idx in range(total_saves):
    # 保存当前观测
    save_file = save_observation(observations["rgb"], save_idx, "view")
    print(f"\n保存点 {save_idx + 1}/{total_saves}: 保存观测 → {save_file}")

    # 执行多个随机动作以获得更大的运动幅度
    print(f"  执行 {actions_per_save} 个随机动作...")
    for action_idx in range(actions_per_save):
        action = random.choice(actions)
        observations = sim.step(action)
        print(f"    动作 {action_idx + 1}: {action}", end="")
        if (action_idx + 1) % 5 == 0:
            print()  # 每5个动作换行
        else:
            print(", ", end="")

    # 换行（如果上面没有换行）
    if actions_per_save % 5 != 0:
        print()

# 保存最终观测
print(f"\n执行最后一批动作...")
for action_idx in range(actions_per_save):
    action = random.choice(actions)
    observations = sim.step(action)
    print(f"  最终动作 {action_idx + 1}: {action}")

final_file = save_observation(observations["rgb"], 999, "final")
print(f"\n✓ 完成！最终观测已保存: {final_file}")
print(f"✓ 所有图片已保存到 {output_dir}/ 目录")

# 显示生成的文件列表
print(f"\n生成的图片文件:")
for filename in sorted(os.listdir(output_dir)):
    filepath = os.path.join(output_dir, filename)
    filesize = os.path.getsize(filepath)
    print(f"  {filename} ({filesize} bytes)")

sim.close()