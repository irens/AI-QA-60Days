"""
Day 76: 性能压测深度实践(1) - 负载生成策略
目标：设计符合业务特征的负载模型
测试架构师视角：负载模型选择、参数配置、负载生成执行
"""

from dataclasses import dataclass
from typing import List, Dict, Callable
from enum import Enum
import random
import math


class LoadModel(Enum):
    """负载模型类型"""
    CONSTANT = "恒定负载"
    STEP = "阶梯负载"
    SPIKE = "脉冲负载"
    WAVE = "波浪负载"


@dataclass
class LoadConfig:
    """负载配置"""
    model: LoadModel
    initial_users: int
    max_users: int
    duration_seconds: int
    think_time_min: float
    think_time_max: float


@dataclass
class LoadSnapshot:
    """负载快照"""
    timestamp: int
    concurrent_users: int
    requests_per_second: float


class LoadGenerator:
    """负载生成器"""

    def __init__(self, config: LoadConfig):
        self.config = config
        self.snapshots: List[LoadSnapshot] = []

    def generate_constant_load(self) -> List[LoadSnapshot]:
        """生成恒定负载"""
        snapshots = []
        for t in range(0, self.config.duration_seconds, 10):
            snapshot = LoadSnapshot(
                timestamp=t,
                concurrent_users=self.config.max_users,
                requests_per_second=self.config.max_users / random.uniform(
                    self.config.think_time_min, self.config.think_time_max
                )
            )
            snapshots.append(snapshot)
        return snapshots

    def generate_step_load(self) -> List[LoadSnapshot]:
        """生成阶梯负载"""
        snapshots = []
        step_duration = self.config.duration_seconds // 5
        step_increment = (self.config.max_users - self.config.initial_users) // 5

        for step in range(5):
            users = self.config.initial_users + step * step_increment
            for t in range(step * step_duration, (step + 1) * step_duration, 10):
                snapshot = LoadSnapshot(
                    timestamp=t,
                    concurrent_users=users,
                    requests_per_second=users / random.uniform(
                        self.config.think_time_min, self.config.think_time_max
                    )
                )
                snapshots.append(snapshot)
        return snapshots

    def generate_spike_load(self) -> List[LoadSnapshot]:
        """生成脉冲负载"""
        snapshots = []
        # 预热期
        for t in range(0, 60, 10):
            users = int(self.config.initial_users + (self.config.max_users - self.config.initial_users) * t / 60)
            snapshots.append(LoadSnapshot(
                timestamp=t,
                concurrent_users=users,
                requests_per_second=users / self.config.think_time_min
            ))

        # 脉冲峰值
        for t in range(60, 120, 10):
            snapshots.append(LoadSnapshot(
                timestamp=t,
                concurrent_users=self.config.max_users,
                requests_per_second=self.config.max_users / self.config.think_time_min
            ))

        # 恢复期
        for t in range(120, self.config.duration_seconds, 10):
            decay_factor = math.exp(-(t - 120) / 60)
            users = int(self.config.initial_users + (self.config.max_users - self.config.initial_users) * decay_factor)
            snapshots.append(LoadSnapshot(
                timestamp=t,
                concurrent_users=users,
                requests_per_second=users / random.uniform(
                    self.config.think_time_min, self.config.think_time_max
                )
            ))

        return snapshots

    def generate_wave_load(self) -> List[LoadSnapshot]:
        """生成波浪负载"""
        snapshots = []
        for t in range(0, self.config.duration_seconds, 10):
            # 使用正弦波模拟高峰低谷
            wave = math.sin(t * 2 * math.pi / 120)  # 2分钟一个周期
            users = int(self.config.initial_users + 
                       (self.config.max_users - self.config.initial_users) * (0.5 + 0.5 * wave))
            snapshots.append(LoadSnapshot(
                timestamp=t,
                concurrent_users=users,
                requests_per_second=users / random.uniform(
                    self.config.think_time_min, self.config.think_time_max
                )
            ))
        return snapshots

    def generate(self) -> List[LoadSnapshot]:
        """根据配置生成负载"""
        generators = {
            LoadModel.CONSTANT: self.generate_constant_load,
            LoadModel.STEP: self.generate_step_load,
            LoadModel.SPIKE: self.generate_spike_load,
            LoadModel.WAVE: self.generate_wave_load
        }

        generator = generators.get(self.config.model, self.generate_constant_load)
        self.snapshots = generator()
        return self.snapshots

    def get_statistics(self) -> Dict:
        """获取负载统计信息"""
        if not self.snapshots:
            return {}

        users = [s.concurrent_users for s in self.snapshots]
        rps = [s.requests_per_second for s in self.snapshots]

        total_requests = sum(rps) * 10  # 每10秒一个快照

        return {
            "total_requests": int(total_requests),
            "avg_concurrent_users": int(sum(users) / len(users)),
            "peak_concurrent_users": max(users),
            "min_concurrent_users": min(users),
            "avg_rps": round(sum(rps) / len(rps), 1),
            "peak_rps": round(max(rps), 1)
        }


def demonstrate_load_models():
    """演示不同负载模型"""
    lines = []
    lines.append("=" * 70)
    lines.append("Day 76: 性能压测深度实践(1) - 负载生成策略")
    lines.append("测试架构师视角：设计符合业务特征的负载模型")
    lines.append("=" * 70)
    lines.append("")

    # 场景1: 电商大促 - 脉冲负载
    lines.append("【场景1】电商平台大促活动")
    lines.append("  业务特征: 秒杀场景，突发流量")
    lines.append("  选择模型: 脉冲负载模型 (Spike Load)")
    lines.append("  选择理由: 模拟秒杀开始时的突发流量特征")
    lines.append("")

    spike_config = LoadConfig(
        model=LoadModel.SPIKE,
        initial_users=100,
        max_users=5000,
        duration_seconds=300,
        think_time_min=0.5,
        think_time_max=2.0
    )

    spike_generator = LoadGenerator(spike_config)
    spike_generator.generate()
    spike_stats = spike_generator.get_statistics()

    lines.append("【负载参数配置】")
    lines.append(f"  并发用户数: {spike_config.initial_users} → {spike_config.max_users} (脉冲模式)")
    lines.append(f"  思考时间: {spike_config.think_time_min}-{spike_config.think_time_max}秒 (高压场景)")
    lines.append(f"  持续时间: {spike_config.duration_seconds}秒")
    lines.append("")

    lines.append("【负载生成执行】")
    lines.append("  时间轴: 0s    60s   120s  180s  240s  300s")

    # 生成用户数时间线
    user_timeline = []
    for i, snapshot in enumerate(spike_generator.snapshots[::3]):  # 每30秒取一个点
        user_timeline.append(f"{snapshot.concurrent_users}")
    lines.append(f"  用户数: {' → '.join(user_timeline)}")
    lines.append("")

    lines.append("【负载生成统计】")
    lines.append(f"  总请求数: {spike_stats['total_requests']:,}")
    lines.append(f"  平均并发: {spike_stats['avg_concurrent_users']:,}")
    lines.append(f"  峰值并发: {spike_stats['peak_concurrent_users']:,}")
    lines.append(f"  平均RPS: {spike_stats['avg_rps']}")
    lines.append(f"  峰值RPS: {spike_stats['peak_rps']}")
    lines.append("")

    # 场景2: 日常业务 - 波浪负载
    lines.append("【场景2】日常业务流量")
    lines.append("  业务特征: 早晚高峰，周期性波动")
    lines.append("  选择模型: 波浪负载模型 (Wave Load)")
    lines.append("  选择理由: 模拟日常业务的高峰低谷周期")
    lines.append("")

    wave_config = LoadConfig(
        model=LoadModel.WAVE,
        initial_users=500,
        max_users=2000,
        duration_seconds=240,
        think_time_min=2.0,
        think_time_max=5.0
    )

    wave_generator = LoadGenerator(wave_config)
    wave_generator.generate()
    wave_stats = wave_generator.get_statistics()

    lines.append("【负载生成统计】")
    lines.append(f"  总请求数: {wave_stats['total_requests']:,}")
    lines.append(f"  平均并发: {wave_stats['avg_concurrent_users']:,}")
    lines.append(f"  峰值并发: {wave_stats['peak_concurrent_users']:,}")
    lines.append(f"  流量波动: 高峰是低谷的{wave_stats['peak_concurrent_users'] // wave_stats['min_concurrent_users']}倍")
    lines.append("")

    # 场景3: 容量测试 - 阶梯负载
    lines.append("【场景3】系统容量评估")
    lines.append("  业务特征: 逐步加压，寻找性能拐点")
    lines.append("  选择模型: 阶梯负载模型 (Step Load)")
    lines.append("  选择理由: 系统化评估系统在不同负载下的表现")
    lines.append("")

    step_config = LoadConfig(
        model=LoadModel.STEP,
        initial_users=100,
        max_users=1000,
        duration_seconds=250,
        think_time_min=1.0,
        think_time_max=3.0
    )

    step_generator = LoadGenerator(step_config)
    step_generator.generate()
    step_stats = step_generator.get_statistics()

    lines.append("【阶梯负载配置】")
    lines.append(f"  初始用户: {step_config.initial_users}")
    lines.append(f"  每阶梯增量: {(step_config.max_users - step_config.initial_users) // 5}")
    lines.append(f"  阶梯数: 5")
    lines.append(f"  每阶梯持续时间: 50秒")
    lines.append("")

    lines.append("【结论】负载生成策略设计完成")
    lines.append("  脉冲负载: 适用于秒杀/大促场景，验证突发流量应对能力")
    lines.append("  波浪负载: 适用于日常业务，模拟周期性流量特征")
    lines.append("  阶梯负载: 适用于容量评估，系统化寻找性能拐点")
    lines.append("  恒定负载: 适用于稳定性测试，长时间恒定压力验证")
    lines.append("")

    return "\n".join(lines)


def main():
    """主函数"""
    report = demonstrate_load_models()
    print(report)


if __name__ == "__main__":
    main()
