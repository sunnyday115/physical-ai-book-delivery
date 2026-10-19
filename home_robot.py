"""食卓・ソファ・ホームの座標を保存し、名前を指定して移動する。"""

import argparse
import json
import math
import subprocess
import sys
import time
from pathlib import Path


LABELS = {"home": "ホーム", "table": "食卓", "sofa": "ソファ", "bed": "ベッド"}
CONFIG = Path.home() / "pai_beginner_ws/home_destinations.json"


def read_pose():
    """ROS 2のコマンド補助プロセスを使わず、現在の位置を1件受信する。"""
    import rclpy
    from nav_msgs.msg import Odometry

    rclpy.init()
    node = rclpy.create_node("read_home_position")
    received = []
    subscription = node.create_subscription(Odometry, "/odom", received.append, 10)
    try:
        deadline = time.monotonic() + 5.0
        while not received and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.1)
        if not received:
            raise ValueError("位置情報を受信できません。Gazeboの再生とブリッジを確認してください")
        message = received[-1]
        p = message.pose.pose.position
        v = message.twist.twist
        if not all(math.isfinite(n) for n in (p.x, p.y, v.linear.x, v.angular.z)):
            raise ValueError("位置・速度情報が不正です")
        if abs(v.linear.x) > 0.01 or abs(v.angular.z) > 0.02:
            raise ValueError("ロボットを停止させてから操作してください")
        if not message.header.frame_id:
            raise ValueError("位置情報に座標系の名前がありません")
        return p.x, p.y, message.header.frame_id
    finally:
        node.destroy_subscription(subscription)
        node.destroy_node()
        rclpy.shutdown()


def load_config(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data.get("frame_id"), str) or not data["frame_id"]:
        raise ValueError("設定のframe_idが不正です")
    for name in LABELS:
        point = data["destinations"][name]
        for axis in ("x", "y"):
            value = point[axis]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError("座標は数値で指定してください")
            if not math.isfinite(value):
                raise ValueError("座標は有限の数値で指定してください")
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("register", "list", "go"))
    parser.add_argument("destination", choices=tuple(LABELS), nargs="?")
    parser.add_argument("--config", type=Path, default=CONFIG)
    args = parser.parse_args()
    if args.operation == "go" and args.destination is None:
        parser.error("goの後にhome・table・sofaのどれかを指定してください")
    if args.operation != "go" and args.destination is not None:
        parser.error("行き先を付けるのはgoの場合だけです")

    try:
        if args.operation == "register":
            if args.config.exists():
                raise ValueError("行き先は登録済みです。listで確認してください（上書きしません）")
            x, y, frame = read_pose()
            data = {
                "frame_id": frame,
                "destinations": {
                    "home": {"x": x, "y": y},
                    "table": {"x": x + 1.5, "y": y},
                    "sofa": {"x": x, "y": y + 1.5},
                },
            }
            with args.config.open("x", encoding="utf-8") as stream:
                json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
                stream.write("\n")
            print(f"現在位置をホームとして登録しました：{args.config}", flush=True)
        else:
            data = load_config(args.config)
        for name, label in LABELS.items():
            point = data["destinations"][name]
            print(f"{name}（{label}）：x={point['x']:.3f}, y={point['y']:.3f}", flush=True)

        if args.operation == "go":
            _, _, frame = read_pose()
            if frame != data["frame_id"]:
                raise ValueError("登録時と現在の座標系が異なります。移動しません")
            controller = Path(__file__).with_name("go_to_point.py")
            if not controller.is_file():
                controller = Path(__file__).parent.parent / "step6/go_to_point.py"
            if not controller.is_file():
                raise ValueError("go_to_point.pyが見つかりません")
            point = data["destinations"][args.destination]
            print(f"{LABELS[args.destination]}へ移動します", flush=True)
            return subprocess.call(
                [
                    sys.executable,
                    str(controller),
                    "--ros-args",
                    "-p",
                    "relative:=false",
                    "-p",
                    f"goal_x:={float(point['x'])}",
                    "-p",
                    f"goal_y:={float(point['y'])}",
                ]
            )
        return 0
    except KeyboardInterrupt:
        # 端末からのCtrl+Cは子の制御プログラムにも届き、子が停止指令を送る。
        print("操作を中断しました。移動中の場合は停止ログを確認してください")
        return 1
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f"実行しません：{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
