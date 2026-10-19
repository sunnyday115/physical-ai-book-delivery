"""登録済みの3地点に、物理的な衝突のないGazebo表示マーカーを置く。"""

import argparse
import json
import math
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path


NAMESPACE = "pai_home_destinations"
PLACES = {
    "home": ("HOME", (0.15, 0.65, 1.0)),
    "table": ("TABLE", (1.0, 0.7, 0.1)),
    "sofa": ("SOFA", (0.35, 0.85, 0.35)),
    "bed": ("BED", (0.8, 0.3, 0.8)),
}
# FortressではTEXTの文字列が描画へ渡らないため、文字の形を三角形で描く。
# 画面の文字は英字、教材側の対応表は日本語にする。
FONT = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
}
DEFAULT_CONFIG = Path.home() / "pai_beginner_ws/home_destinations.json"


def label_points(label):
    """英字の各画素を、両側から見える小さな長方形として表す。"""
    points = []
    width = (len(label) * 6 - 1) * 0.045
    for index, char in enumerate(label):
        for row, pattern in enumerate(FONT[char]):
            for col, value in enumerate(pattern):
                if value == "0":
                    continue
                left = width / 2 - (index * 6 + col) * 0.045
                right = left - 0.045
                bottom = (6 - row) * 0.06
                top = bottom + 0.06
                a, b, c, d = (left, bottom), (right, bottom), (right, top), (left, top)
                for y, z in (a, b, c, a, c, d, c, b, a, d, c, a):
                    points.append(f"point: {{x: 0, y: {y:.4f}, z: {z:.4f}}}")
    return ", ".join(points)


def run_ign(arguments, allow_no_reply=False):
    result = subprocess.run(
        ["ign", *arguments], capture_output=True, text=True, timeout=12, check=True
    )
    if not allow_no_reply and "timed out" in (result.stdout + result.stderr).lower():
        raise ValueError("Gazeboのサービス呼び出しがタイムアウトしました")
    return result.stdout


def send_marker(request):
    run_ign(
        [
            "service",
            "-s",
            "/marker",
            "--reqtype",
            "ignition.msgs.Marker",
            "--reptype",
            "ignition.msgs.Empty",
            "--timeout",
            "1000",
            "--req",
            request,
        ],
        # Fortressの/markerは登録できてもEmptyの返信を返さない。
        # この呼び出しの完了だけで成功とせず、後で一覧と画面を確認する。
        allow_no_reply=True,
    )


def registered_ids():
    listing = run_ign(
        [
            "service",
            "-s",
            "/marker/list",
            "--reqtype",
            "ignition.msgs.Empty",
            "--reptype",
            "ignition.msgs.Marker_V",
            "--timeout",
            "3000",
            "--req",
            "",
        ]
    )
    return {
        int(value)
        for value in re.findall(r'ns: "pai_home_destinations"\s+id: (\d+)', listing)
    }


def read_robot_pose():
    import rclpy
    from nav_msgs.msg import Odometry
    from rclpy.signals import SignalHandlerOptions

    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    node = rclpy.create_node("home_marker_alignment")
    messages = []
    subscription = node.create_subscription(Odometry, "/odom", messages.append, 10)
    try:
        # マーカー配置時には停止中のロボットを使い、2つの座標を照合する。
        for _ in range(50):
            rclpy.spin_once(node, timeout_sec=0.1)
            if messages:
                break
        if not messages:
            raise ValueError("位置情報がありません。Gazeboを再生状態にしてください")
        message = messages[-1]
        p = message.pose.pose.position
        q = message.pose.pose.orientation
        v = message.twist.twist
        values = (p.x, p.y, q.x, q.y, q.z, q.w, v.linear.x, v.angular.z)
        if not all(math.isfinite(value) for value in values):
            raise ValueError("位置・速度情報に不正な数値があります")
        if abs(v.linear.x) > 0.01 or abs(v.angular.z) > 0.02:
            raise ValueError("停止してからマーカーを追加してください")
        yaw = math.atan2(
            2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z)
        )
        output = run_ign(["model", "-m", "beginner_robot", "-p"])
        pairs = re.findall(
            r"\[\s*([-+\d.eE]+)\s+([-+\d.eE]+)\s+([-+\d.eE]+)\s*\]", output
        )
        if len(pairs) != 2:
            raise ValueError("Gazeboのロボット位置を読み取れませんでした")
        model_x, model_y, _ = map(float, pairs[0])
        _, _, world_yaw = map(float, pairs[1])
        # DiffDriveは左右輪の中点を走行計算の基準とする。
        # このモデルの左右輪はモデル原点より約0.554m前にある。
        root = ET.parse(Path.home() / "pai_step1_edit.sdf").getroot()
        model = root.find(".//model[@name='beginner_robot']")
        centers = []
        for name in ("left_wheel", "right_wheel"):
            pose = model.find(f"link[@name='{name}']/pose")
            if pose is None or pose.get("relative_to"):
                raise ValueError("左右輪のモデル内位置を読み取れませんでした")
            centers.append([float(value) for value in pose.text.split()[:2]])
        axle_x = (centers[0][0] + centers[1][0]) / 2
        axle_y = (centers[0][1] + centers[1][1]) / 2
        world_x = model_x + math.cos(world_yaw) * axle_x - math.sin(world_yaw) * axle_y
        world_y = model_y + math.sin(world_yaw) * axle_x + math.cos(world_yaw) * axle_y
        return {
            "frame_id": message.header.frame_id,
            "odom_x": p.x,
            "odom_y": p.y,
            "odom_yaw": yaw,
            "world_x": world_x,
            "world_y": world_y,
            "world_yaw": world_yaw,
            "model_x": model_x,
            "model_y": model_y,
            "axle_offset_x": axle_x,
            "axle_offset_y": axle_y,
        }
    finally:
        node.destroy_subscription(subscription)
        node.destroy_node()
        rclpy.shutdown()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--remove", action="store_true")
    args = parser.parse_args()
    try:
        if args.remove:
            for marker_id in range(1, len(PLACES) * 2 + 1):
                send_marker(
                    f'ns: "{NAMESPACE}", id: {marker_id}, action: DELETE_MARKER'
                )
            if registered_ids() & set(range(1, len(PLACES) * 2 + 1)):
                raise ValueError("マーカーの削除を確認できませんでした")
            print("今回の床マーカーとラベルだけを削除しました")
            return 0

        data = json.loads(args.config.read_text(encoding="utf-8"))
        alignment = read_robot_pose()
        if data["frame_id"] != alignment["frame_id"]:
            raise ValueError("登録時と現在の座標系が異なります")
        angle = alignment["world_yaw"] - alignment["odom_yaw"]
        c, s = math.cos(angle), math.sin(angle)
        for index, (name, (label, color)) in enumerate(PLACES.items()):
            point = data["destinations"][name]
            dx = float(point["x"]) - alignment["odom_x"]
            dy = float(point["y"]) - alignment["odom_y"]
            if not all(math.isfinite(value) for value in (dx, dy)):
                raise ValueError("登録座標が不正です")
            x = alignment["world_x"] + c * dx - s * dy
            y = alignment["world_y"] + s * dx + c * dy
            common = f'ns: "{NAMESPACE}", action: ADD_MODIFY'
            r, g, b = color
            rgba = f"r: {r}, g: {g}, b: {b}, a: 1"
            material = f"material: {{ambient: {{{rgba}}}, diffuse: {{{rgba}}}}}"
            send_marker(
                f"{common}, id: {index * 2 + 1}, type: CYLINDER, "
                f"pose: {{position: {{x: {x}, y: {y}, z: 0.015}}}}, "
                f"scale: {{x: 1.1, y: 1.1, z: 0.025}}, {material}"
            )
            label_height = 1.8 if name == "table" else 1.2
            send_marker(
                f"{common}, id: {index * 2 + 2}, type: TRIANGLE_LIST, "
                f"pose: {{position: {{x: {x}, y: {y}, z: {label_height}}}}}, "
                f"scale: {{x: 1, y: 1, z: 1}}, {material}, {label_points(label)}"
            )
            print(f"{label}を表示：Gazebo座標 x={x:.3f}, y={y:.3f}", flush=True)
        path = args.config.with_name("home_marker_alignment.json")
        path.write_text(
            json.dumps(alignment, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        if registered_ids() != set(range(1, len(PLACES) * 2 + 1)):
            raise ValueError("必要なマーカーすべての登録を確認できませんでした")
        print("表示のみのマーカーです。物理的な衝突はありません")
        return 0
    except (
        ValueError,
        OSError,
        KeyError,
        TypeError,
        ET.ParseError,
        subprocess.SubprocessError,
    ) as error:
        print(f"表示を完了できませんでした：{error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
