#!/usr/bin/env python3

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import HistoryPolicy
from rclpy.qos import QoSProfile
from rclpy.qos import ReliabilityPolicy
from sensor_msgs.msg import CameraInfo
from sensor_msgs.msg import Image


class RestampRealSenseRgbd(Node):
    def __init__(self):
        super().__init__("restamp_realsense_rgbd")

        input_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=ReliabilityPolicy.BEST_EFFORT,
        )
        output_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=ReliabilityPolicy.BEST_EFFORT,
        )

        self._latest_color = None
        self._latest_depth = None
        self._latest_info = None
        self._color_count = 0
        self._depth_count = 0
        self._last_pair = None

        self._color_publisher = self.create_publisher(
            Image,
            self._topic("color_image_out", "/camera_odom_d555/color/image_raw"),
            output_qos,
        )
        self._depth_publisher = self.create_publisher(
            Image,
            self._topic("depth_image_out", "/camera_odom_d555/aligned_depth_to_color/image_raw"),
            output_qos,
        )
        self._info_publisher = self.create_publisher(
            CameraInfo,
            self._topic("color_info_out", "/camera_odom_d555/color/camera_info"),
            output_qos,
        )

        self.create_subscription(
            Image,
            self._topic("color_image_in", "/camera/color/image_raw"),
            self._store_color,
            input_qos,
        )
        self.create_subscription(
            Image,
            self._topic("depth_image_in", "/camera/aligned_depth_to_color/image_raw"),
            self._store_depth,
            input_qos,
        )
        self.create_subscription(
            CameraInfo,
            self._topic("color_info_in", "/camera/color/camera_info"),
            self._store_info,
            input_qos,
        )

    def _topic(self, name, default_value):
        self.declare_parameter(name, default_value)
        return self.get_parameter(name).value

    def _store_color(self, message):
        self._latest_color = message
        self._color_count += 1
        self._publish_pair()

    def _store_depth(self, message):
        self._latest_depth = message
        self._depth_count += 1
        self._publish_pair()

    def _store_info(self, message):
        self._latest_info = message
        self._publish_pair()

    def _publish_pair(self):
        if self._latest_color is None or self._latest_depth is None or self._latest_info is None:
            return

        pair = (self._color_count, self._depth_count)
        if pair == self._last_pair:
            return
        self._last_pair = pair

        stamp = self.get_clock().now().to_msg()
        self._latest_color.header.stamp = stamp
        self._latest_depth.header.stamp = stamp
        self._latest_info.header.stamp = stamp

        self._color_publisher.publish(self._latest_color)
        self._depth_publisher.publish(self._latest_depth)
        self._info_publisher.publish(self._latest_info)


def main():
    rclpy.init()
    node = RestampRealSenseRgbd()

    cleaned_up = False

    def cleanup():
        nonlocal cleaned_up
        if cleaned_up:
            return
        cleaned_up = True
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        cleanup()


if __name__ == "__main__":
    main()
