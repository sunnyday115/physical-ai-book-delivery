"""目標点へ向きを合わせて前進し、到着・停止をオドメトリで確認する。"""

import math
import time

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions


class GoToPoint(Node):
    def __init__(self):
        super().__init__("go_to_point")
        self.declare_parameter("goal_x", 1.0)
        self.declare_parameter("goal_y", 1.0)
        self.declare_parameter("relative", True)
        self.request_x = float(self.get_parameter("goal_x").value)
        self.request_y = float(self.get_parameter("goal_y").value)
        self.relative = self.get_parameter("relative").value
        if not all(math.isfinite(v) for v in (self.request_x, self.request_y)):
            raise ValueError("目標座標は有限の数値で指定してください")
        self.publisher = self.create_publisher(Twist, "/cmd_vel", 10)
        self.subscription = self.create_subscription(
            Odometry, "/odom", self.receive_odom, 10
        )
        self.goal = None
        self.position = None
        self.yaw = 0.0
        self.linear_speed = 0.0
        self.angular_speed = 0.0
        self.last_received = None
        self.started = time.monotonic()
        self.state = "WAIT"
        self.stop_started = None
        self.arrival = False
        self.completed = False
        self.succeeded = False
        self.timer = self.create_timer(0.1, self.control)
        self.get_logger().info("位置情報を待っています")

    def receive_odom(self, message):
        p = message.pose.pose.position
        q = message.pose.pose.orientation
        v = message.twist.twist
        if not all(
            math.isfinite(n)
            for n in (p.x, p.y, q.x, q.y, q.z, q.w, v.linear.x, v.angular.z)
        ):
            self.begin_stop("位置・速度情報が不正なため停止します")
            return
        self.position = (p.x, p.y)
        self.yaw = math.atan2(
            2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z)
        )
        self.linear_speed = v.linear.x
        self.angular_speed = v.angular.z
        self.last_received = time.monotonic()
        if self.goal is None and self.state == "WAIT":
            self.goal = (
                (p.x + self.request_x, p.y + self.request_y)
                if self.relative
                else (self.request_x, self.request_y)
            )
            self.get_logger().info(f"開始位置 x={p.x:.6f}, y={p.y:.6f}")
            self.get_logger().info(
                f"目標位置 x={self.goal[0]:.6f}, y={self.goal[1]:.6f}"
            )
            if self.distance() > 5.0:
                self.begin_stop("目標が5mより遠いため実行しません")
            else:
                self.state = "TURN"
                self.get_logger().info("目標の方向へ旋回します")

    def distance(self):
        if self.goal is None or self.position is None:
            return math.inf
        return math.hypot(
            self.goal[0] - self.position[0], self.goal[1] - self.position[1]
        )

    def begin_stop(self, reason, arrival=False):
        if self.state != "STOP":
            self.state = "STOP"
            self.stop_started = time.monotonic()
            self.arrival = arrival
            self.get_logger().info(reason)

    def control(self):
        now = time.monotonic()
        command = Twist()
        fresh = self.last_received is not None and now - self.last_received < 1.0
        if self.state != "STOP":
            if self.position is None and now - self.started > 3.0:
                self.begin_stop("位置情報を3秒受信できないため中止します")
            elif self.position is not None and not fresh:
                self.begin_stop("位置情報が1秒以上途絶えたため停止します")
            elif now - self.started > 90.0:
                self.begin_stop("90秒以内に到着しないため停止します")
            elif self.goal is not None:
                distance = self.distance()
                angle = math.atan2(
                    self.goal[1] - self.position[1],
                    self.goal[0] - self.position[0],
                )
                error = math.atan2(
                    math.sin(angle - self.yaw), math.cos(angle - self.yaw)
                )
                if distance <= 0.05:
                    self.begin_stop(
                        f"目標まで残り{distance:.3f}mで停止指令へ切替", arrival=True
                    )
                else:
                    if self.state == "TURN" and abs(error) < math.radians(5):
                        self.state = "DRIVE"
                        self.get_logger().info("向きが合いました。目標へ前進します")
                    elif self.state == "DRIVE" and abs(error) > math.radians(20):
                        self.state = "TURN"
                        self.get_logger().info("いったん前進を止め、向きを合わせ直します")
                    command.angular.z = max(-0.5, min(0.5, error * 1.5))
                    if self.state == "DRIVE":
                        command.linear.x = min(0.2, distance * 0.8)
        self.publisher.publish(command)
        if self.state == "STOP" and now - self.stop_started >= 1.0:
            stopped = (
                fresh
                and abs(self.linear_speed) < 0.01
                and abs(self.angular_speed) < 0.02
            )
            if stopped or now - self.stop_started > 3.0:
                self.succeeded = self.arrival and stopped and self.distance() <= 0.07
                result = "到着・停止を確認" if self.succeeded else "未達または停止未確認"
                self.get_logger().info(f"{result}：目標まで残り{self.distance():.3f}m")
                if self.position is not None:
                    self.get_logger().info(
                        f"終了位置 x={self.position[0]:.6f}, y={self.position[1]:.6f}"
                    )
                self.completed = True
                self.timer.cancel()


def main():
    # ROS通信を終了する前にCtrl+Cを受け取り、停止指令を送る。
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    node = None
    success = False
    try:
        node = GoToPoint()
        while rclpy.ok() and not node.completed:
            rclpy.spin_once(node, timeout_sec=0.1)
        success = node.succeeded
    except KeyboardInterrupt:
        if node is not None:
            node.get_logger().info("操作を中断し、停止指令を送ります")
    finally:
        if node is not None:
            for _ in range(10):
                node.publisher.publish(Twist())
                time.sleep(0.1)
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
