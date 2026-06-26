#!/usr/bin/env python3

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import HistoryPolicy
from rclpy.qos import QoSProfile
from rclpy.qos import ReliabilityPolicy
from sensor_msgs.msg import CameraInfo
from sensor_msgs.msg import Image
from sensor_msgs.msg import Imu


class RestampRealSenseStereo(Node):
    def __init__(self):
        super().__init__("restamp_realsense_stereo")
        self.declare_parameter("enable_imu", False)

        self._qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=ReliabilityPolicy.RELIABLE,
        )

        self._relay(
            Image,
            self._topic("left_image_in", "/camera/camera/infra1/image_rect_raw"),
            self._topic("left_image_out", "/camera_odom_d555/infra1/image_rect_raw"),
        )
        self._relay(
            CameraInfo,
            self._topic("left_info_in", "/camera/camera/infra1/camera_info"),
            self._topic("left_info_out", "/camera_odom_d555/infra1/camera_info"),
        )
        self._relay(
            Image,
            self._topic("right_image_in", "/camera/camera/infra2/image_rect_raw"),
            self._topic("right_image_out", "/camera_odom_d555/infra2/image_rect_raw"),
        )
        self._relay(
            CameraInfo,
            self._topic("right_info_in", "/camera/camera/infra2/camera_info"),
            self._topic("right_info_out", "/camera_odom_d555/infra2/camera_info"),
        )
        if self.get_parameter("enable_imu").value:
            self._relay(
                Imu,
                self._topic("imu_in", "/camera_odom_d555/imu/data_filtered"),
                self._topic("imu_out", "/camera_odom_d555/imu/data"),
            )

    def _topic(self, name, default_value):
        self.declare_parameter(name, default_value)
        return self.get_parameter(name).value

    def _relay(self, message_type, input_topic, output_topic):
        publisher = self.create_publisher(message_type, output_topic, self._qos)
        self.create_subscription(
            message_type,
            input_topic,
            lambda message, pub=publisher: self._publish_restamped(message, pub),
            self._qos,
        )

    def _publish_restamped(self, message, publisher):
        message.header.stamp = self.get_clock().now().to_msg()
        publisher.publish(message)


def main():
    rclpy.init()
    node = RestampRealSenseStereo()

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
