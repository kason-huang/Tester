import habitat_sim

# 创建仿真配置
sim_settings = {
    "scene_id": "data/scene_datasets/hm3d/00000-kfPV7w3FaU5/kfPV7w3FaU5.basis.glb",
    "sensor_height": 1.5,
    "sensor_pitch": 0,
    "hfov": "90",
    "enable_glfw": True,
}

# 创建仿真器配置 - 使用字典方式
backend_cfg = habitat_sim.SimulatorConfiguration()
backend_cfg.scene_id = sim_settings["scene_id"]
backend_cfg.gpu_device_id = 0

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
print("✓ 仿真器运行成功!")
print(f"可用的观测键: {list(observations.keys())}")
# 检查每个观测的形状
for key, value in observations.items():
    if hasattr(value, 'shape'):
        print(f"  {key}: {value.shape}")
    else:
        print(f"  {key}: {type(value)}")

sim.close()