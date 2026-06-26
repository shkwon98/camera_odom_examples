import importlib.util
from pathlib import Path

import os

from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch_ros.actions import Node


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def _load_launch(path: Path):
    spec = importlib.util.spec_from_file_location(path.name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.generate_launch_description()


def _assert_rviz_config(path: Path, expected_topics: tuple[str, ...]):
    assert path.is_file()
    rviz_text = path.read_text()
    for expected_text in (
        "Class: rviz_default_plugins/TF",
        "Class: rviz_default_plugins/Path",
        "Class: rviz_default_plugins/Odometry",
        "Shape:",
        "Axes Length: 0.12",
        "Axes Radius: 0.012",
        "Value: Axes",
        "Class: rviz_default_plugins/PointCloud2",
        "Class: rviz_default_plugins/Image",
    ):
        assert expected_text in rviz_text
    assert "Shape: Axes" not in rviz_text
    for topic in expected_topics:
        assert topic in rviz_text


def test_package_metadata_declares_d555_visual_slam_test():
    cmake_lists = (PACKAGE_ROOT / "CMakeLists.txt").read_text()
    package_xml = (PACKAGE_ROOT / "package.xml").read_text()

    assert "test_realsense_d555_visual_slam_launch" in cmake_lists
    assert "install(PROGRAMS scripts/restamp_realsense_rgbd.py" in cmake_lists
    assert "<exec_depend>rclpy</exec_depend>" in package_xml
    assert "<exec_depend>sensor_msgs</exec_depend>" in package_xml


def test_realsense_d555_visual_slam_launch_builds_rgbd_graph():
    launch_file = PACKAGE_ROOT / "launch" / "realsense_d555_visual_slam.launch.py"
    launch_text = launch_file.read_text()
    entities = _load_launch(launch_file).entities

    argument_names = [
        entity.name
        for entity in entities
        if isinstance(entity, DeclareLaunchArgument)
    ]

    assert argument_names == [
        "depth_profile",
        "color_profile",
        "image_jitter_threshold_ms",
        "sync_matching_threshold_ms",
        "launch_rviz",
    ]

    assert sum(isinstance(entity, IncludeLaunchDescription) for entity in entities) == 0
    assert sum(isinstance(entity, OpaqueFunction) for entity in entities) == 1
    assert any(
        isinstance(entity, Node)
        and entity.node_package == "rviz2"
        and entity.node_executable == "rviz2"
        for entity in entities
    )

    for expected_text in (
        "def _launch_setup(context, *args, **kwargs):",
        "realsense2_camera",
        "realsense2_camera_node",
        "restamp_realsense_rgbd.py",
        "nvidia::isaac_ros::visual_slam::VisualSlamNode",
        '"device_type": "d555"',
        '"enable_infra": False',
        '"enable_infra1": False',
        '"enable_infra2": False',
        '"enable_gyro": False',
        '"enable_accel": False',
        '"enable_motion": False',
        '"tracking_mode": 2',
        '"depth_scale_factor": 1000.0',
        '"align_depth.enable": True',
        '"enable_sync": True',
        '"depth_module.depth_profile": depth_profile',
        '"rgb_camera.color_profile": color_profile',
        '"depth_module.emitter_enabled": True',
        '"color_image_in": "/camera/color/image_raw"',
        '"color_image_out": "/camera_odom_d555/color/image_raw"',
        '"depth_image_in": "/camera/aligned_depth_to_color/image_raw"',
        '"depth_image_out": "/camera_odom_d555/aligned_depth_to_color/image_raw"',
        '"color_info_in": "/camera/color/camera_info"',
        '"color_info_out": "/camera_odom_d555/color/camera_info"',
        '"base_frame": "camera_link"',
        '"camera_optical_frames": ["camera_color_optical_frame"]',
        '"enable_slam_visualization": False',
        '"enable_localization_n_mapping": False',
        '"publish_map_to_odom_tf": False',
        '"publish_odom_to_base_tf": True',
        '("visual_slam/image_0", "/camera_odom_d555/color/image_raw")',
        '("visual_slam/camera_info_0", "/camera_odom_d555/color/camera_info")',
        '("visual_slam/depth_0", "/camera_odom_d555/aligned_depth_to_color/image_raw")',
        'DeclareLaunchArgument("depth_profile", default_value="640,360,30")',
        'DeclareLaunchArgument("color_profile", default_value="640,360,30")',
        'DeclareLaunchArgument("image_jitter_threshold_ms", default_value="34.0")',
        'DeclareLaunchArgument("launch_rviz", default_value="true")',
        'IfCondition(LaunchConfiguration("launch_rviz"))',
        '"realsense_d555_visual_slam.rviz"',
    ):
        assert expected_text in launch_text

    _assert_rviz_config(
        PACKAGE_ROOT / "rviz" / "realsense_d555_visual_slam.rviz",
        (
            "/visual_slam/tracking/odometry",
            "/visual_slam/tracking/vo_path",
            "/visual_slam/tracking/slam_path",
            "/visual_slam/vis/landmarks_cloud",
            "/visual_slam/vis/observations_cloud",
            "/camera_odom_d555/color/image_raw",
            "/camera_odom_d555/aligned_depth_to_color/image_raw",
        ),
    )

    restamp_script = PACKAGE_ROOT / "scripts" / "restamp_realsense_rgbd.py"
    assert restamp_script.is_file()
    assert os.access(restamp_script, os.X_OK)
    restamp_text = restamp_script.read_text()
    for expected_text in (
        "class RestampRealSenseRgbd(Node):",
        "self.get_clock().now().to_msg()",
        "Image",
        "CameraInfo",
        "create_subscription",
        "create_publisher",
        "input_qos",
        "output_qos",
        "ReliabilityPolicy.BEST_EFFORT",
        "ReliabilityPolicy.RELIABLE",
    ):
        assert expected_text in restamp_text
    assert "signal.signal" not in restamp_text

    for removed_argument in (
        "camera_name",
        "camera_namespace",
        "device_type",
        "emitter_enabled",
        "base_frame",
        "camera_optical_frames",
        "depth_scale_factor",
        "enable_localization_n_mapping",
        "publish_map_to_odom_tf",
        "publish_odom_to_base_tf",
        "enable_ground_constraint_in_odometry",
        "enable_ground_constraint_in_slam",
        "enable_slam_visualization",
    ):
        assert f'DeclareLaunchArgument("{removed_argument}"' not in launch_text

    for default_parameter in (
        '"enable_image_denoising": False',
        '"enable_ground_constraint_in_odometry": False',
        '"enable_ground_constraint_in_slam": False',
        '"enable_color": True',
        '"enable_depth": True',
        '"depth_module.enable_auto_exposure": True',
        '"rgb_camera.enable_auto_exposure": True',
        '"decimation_filter.enable": False',
        '"spatial_filter.enable": False',
        '"temporal_filter.enable": False',
        '"hole_filling_filter.enable": False',
    ):
        assert default_parameter not in launch_text
