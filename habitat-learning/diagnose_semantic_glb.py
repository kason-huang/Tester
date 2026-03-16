#!/usr/bin/env python3
"""
诊断 semantic.glb 的传感器行为
"""

import habitat_sim
import numpy as np

def diagnose_scene(scene_path):
    """诊断场景的传感器输出"""
    print(f"\n{'='*60}")
    print(f"诊断场景: {scene_path}")
    print(f"{'='*60}\n")

    backend_cfg = habitat_sim.SimulatorConfiguration()
    backend_cfg.scene_id = scene_path
    backend_cfg.gpu_device_id = 0

    # RGB 传感器
    rgb_sensor_spec = habitat_sim.CameraSensorSpec()
    rgb_sensor_spec.uuid = "rgb"
    rgb_sensor_spec.sensor_type = habitat_sim.SensorType.COLOR
    rgb_sensor_spec.resolution = [256, 256]
    rgb_sensor_spec.position = [0.0, 1.5, 0.0]
    rgb_sensor_spec.hfov = 90.0

    # 深度传感器
    depth_sensor_spec = habitat_sim.CameraSensorSpec()
    depth_sensor_spec.uuid = "depth"
    depth_sensor_spec.sensor_type = habitat_sim.SensorType.DEPTH
    depth_sensor_spec.resolution = [256, 256]
    depth_sensor_spec.position = [0.0, 1.5, 0.0]
    depth_sensor_spec.hfov = 90.0

    # 语义传感器
    semantic_sensor_spec = habitat_sim.CameraSensorSpec()
    semantic_sensor_spec.uuid = "semantic"
    semantic_sensor_spec.sensor_type = habitat_sim.SensorType.SEMANTIC
    semantic_sensor_spec.resolution = [256, 256]
    semantic_sensor_spec.position = [0.0, 1.5, 0.0]
    semantic_sensor_spec.hfov = 90.0

    agent_cfg = habitat_sim.AgentConfiguration()
    agent_cfg.sensor_specifications = [rgb_sensor_spec, depth_sensor_spec, semantic_sensor_spec]

    agent_cfg.action_space = {
        "move_forward": habitat_sim.agent.ActionSpec(
            "move_forward",
            habitat_sim.agent.ActuationSpec(amount=0.25)
        ),
    }

    cfg = habitat_sim.Configuration(backend_cfg, [agent_cfg])

    try:
        sim = habitat_sim.Simulator(cfg)
        observations = sim.reset()

        print("📊 传感器输出分析：\n")

        for sensor_name, data in observations.items():
            print(f"传感器名称: {sensor_name}")
            print(f"  数据类型: {data.dtype}")
            print(f"  数据形状: {data.shape}")

            if isinstance(data, np.ndarray):
                print(f"  最小值: {data.min():.4f}")
                print(f"  最大值: {data.max():.4f}")
                print(f"  唯一值数量: {len(np.unique(data))}")

                # 判断数据类型
                if data.dtype in [np.int32, np.int64, np.uint32, np.uint64]:
                    print(f"  🔍 这是一个整数类型的传感器 -> 可能是语义数据")
                elif data.dtype in [np.float32, np.float64]:
                    if len(np.unique(data)) < 100:
                        print(f"  🔍 浮点数但唯一值很少 -> 可能是语义数据（离散ID）")
                    elif data.min() >= 0 and data.max() <= 1.0:
                        print(f"  🔍 值域在 [0, 1] -> 可能是 RGB（归一化）")
                    else:
                        print(f"  🔍 值域较大 -> 可能是深度数据")

                # 显示前几个值
                print(f"  前5个值: {data.flat[:5]}")
            print()

        sim.close()
        return True

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    base_path = "data/scene_datasets/hm3d/00020-XYyR54sxe6b"

    normal_glb = f"{base_path}/XYyR54sxe6b.basis.glb"
    semantic_glb = f"{base_path}/XYyR54sxe6b.semantic.glb"

    print("\n" + "="*60)
    print("Habitat-Sim Semantic GLB 诊断工具")
    print("="*60)

    # 测试普通 GLB
    print("\n🔵 测试 1: 普通 GLB 文件")
    diagnose_scene(normal_glb)

    # 测试语义 GLB
    print("\n🟢 测试 2: 语义 GLB 文件")
    diagnose_scene(semantic_glb)

    print("\n" + "="*60)
    print("诊断完成！")
    print("="*60)

    print("\n📝 结论：")
    print("对比上面的两个测试结果，找出 semantic.glb 的特殊行为")
    print("特别注意 'rgb' 和 'semantic' 传感器的数据类型差异")


if __name__ == "__main__":
    main()
