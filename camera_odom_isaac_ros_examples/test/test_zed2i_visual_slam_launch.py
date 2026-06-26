import importlib.util
import json
from pathlib import Path

from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
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
        "Shape: Axes",
        "Class: rviz_default_plugins/PointCloud2",
        "Class: rviz_default_plugins/Image",
    ):
        assert expected_text in rviz_text
    for topic in expected_topics:
        assert topic in rviz_text


def test_package_metadata_installs_launch_and_config_files():
    package_xml = (PACKAGE_ROOT / "package.xml").read_text()
    cmake_lists = (PACKAGE_ROOT / "CMakeLists.txt").read_text()

    assert "<name>camera_odom_isaac_ros_examples</name>" in package_xml
    for dependency in (
        "isaac_ros_image_proc",
        "isaac_ros_visual_slam",
        "launch",
        "launch_ros",
        "rclcpp_components",
        "rviz2",
        "zed_components",
        "zed_description",
        "zed_wrapper",
    ):
        assert f"<exec_depend>{dependency}</exec_depend>" in package_xml

    assert "install(DIRECTORY config launch rviz DESTINATION share/${PROJECT_NAME})" in cmake_lists


def test_zed2i_specs_select_zed2i_model_and_frames():
    specs = json.loads(
        (PACKAGE_ROOT / "config" / "zed2i_visual_slam_interface_specs.json").read_text()
    )
    hd720_specs = json.loads(
        (
            PACKAGE_ROOT
            / "config"
            / "zed2i_hd720_visual_slam_interface_specs.json"
        ).read_text()
    )

    assert specs["camera_model"] == "zed2i"
    assert specs["camera_frame"] == "zed2i_camera_center"
    assert specs["camera_resolution"] == {"width": 672, "height": 376}
    assert hd720_specs["camera_model"] == "zed2i"
    assert hd720_specs["camera_frame"] == "zed2i_camera_center"
    assert hd720_specs["camera_resolution"] == {"width": 1280, "height": 720}


def test_zed2i_visual_slam_launch_builds_vga_stereo_odometry_graph():
    launch_file = PACKAGE_ROOT / "launch" / "zed2i_visual_slam.launch.py"
    launch_text = launch_file.read_text()
    entities = _load_launch(launch_file).entities

    argument_names = [
        entity.name
        for entity in entities
        if isinstance(entity, DeclareLaunchArgument)
    ]

    assert argument_names == [
        "interface_specs_file",
        "pub_frame_rate",
        "grab_frame_rate",
        "grab_resolution",
        "image_jitter_threshold_ms",
        "sync_matching_threshold_ms",
        "launch_rviz",
    ]
    assert sum(isinstance(entity, IncludeLaunchDescription) for entity in entities) == 0
    assert any(
        isinstance(entity, Node)
        and entity.node_package == "rviz2"
        and entity.node_executable == "rviz2"
        for entity in entities
    )

    for expected_text in (
        "zed_components",
        "stereolabs::ZedCamera",
        "nvidia::isaac_ros::visual_slam::VisualSlamNode",
        "nvidia::isaac_ros::image_proc::ImageFormatConverterNode",
        "component_container_mt",
        "visual_slam_container = ComposableNodeContainer",
        '"general.grab_resolution": grab_resolution',
        '"general.pub_resolution": "NATIVE"',
        '"depth.depth_mode": "NONE"',
        '"sensors.publish_imu": False',
        '"sensors.publish_imu_tf": False',
        '"tracking_mode": 0',
        '"base_frame": "zed2i_camera_center"',
        '"camera_optical_frames": [',
        '"enable_localization_n_mapping": False',
        '"publish_map_to_odom_tf": False',
        '"publish_odom_to_base_tf": True',
        '"sync_matching_threshold_ms": sync_matching_threshold_ms',
        "zed_left_rgb_converter",
        "vslam_left_mono_converter",
        "zed2i_visual_slam_interface_specs.json",
        'FindPackageShare("camera_odom_isaac_ros_examples")',
        'DeclareLaunchArgument("grab_resolution", default_value="VGA")',
        'DeclareLaunchArgument("sync_matching_threshold_ms", default_value="5.0")',
        'DeclareLaunchArgument("image_jitter_threshold_ms", default_value="34.0")',
        'DeclareLaunchArgument("launch_rviz", default_value="true")',
        'IfCondition(LaunchConfiguration("launch_rviz"))',
        '"zed2i_visual_slam.rviz"',
        "zed2i_camera_center",
        "zed2i_left_camera_frame_optical",
        "zed2i_right_camera_frame_optical",
        "return [robot_state_publisher, visual_slam_container]",
    ):
        assert expected_text in launch_text

    _assert_rviz_config(
        PACKAGE_ROOT / "rviz" / "zed2i_visual_slam.rviz",
        (
            "/visual_slam/tracking/odometry",
            "/visual_slam/tracking/vo_path",
            "/visual_slam/tracking/slam_path",
            "/visual_slam/vis/landmarks_cloud",
            "/visual_slam/vis/observations_cloud",
            "/left/image_rect",
            "/right/image_rect",
        ),
    )

    for removed_text in (
        "isaac_ros_examples.launch.py",
        "zed_stereo_rect,visual_slam",
        "image_format_node_left",
        "image_format_node_right",
        '"imu_frame":',
        '"gyro_noise_density":',
        '"gyro_random_walk":',
        '"accel_noise_density":',
        '"accel_random_walk":',
        '"calibration_frequency":',
        '"imu_jitter_threshold_ms":',
        '"img_mask_top":',
        '"img_mask_bottom":',
        '"img_mask_left":',
        '"img_mask_right":',
        '"enable_image_denoising": False',
        '"enable_ground_constraint_in_odometry": False',
        '"enable_ground_constraint_in_slam": False',
        "\n    container = ComposableNodeContainer",
        '("visual_slam/imu",',
        'DeclareLaunchArgument("enable_ground_constraint_in_odometry"',
        'DeclareLaunchArgument("base_frame"',
        'DeclareLaunchArgument("camera_optical_frames"',
        'DeclareLaunchArgument("tracking_mode"',
        'DeclareLaunchArgument("imu_frame"',
        'DeclareLaunchArgument("imu_topic"',
        'DeclareLaunchArgument("publish_imu"',
        'DeclareLaunchArgument("publish_imu_tf"',
        'DeclareLaunchArgument("imu_pub_rate"',
        'DeclareLaunchArgument("gyro_noise_density"',
        'DeclareLaunchArgument("gyro_random_walk"',
        'DeclareLaunchArgument("accel_noise_density"',
        'DeclareLaunchArgument("accel_random_walk"',
        'DeclareLaunchArgument("calibration_frequency"',
        'DeclareLaunchArgument("enable_localization_n_mapping"',
        'DeclareLaunchArgument("publish_map_to_odom_tf"',
        'DeclareLaunchArgument("publish_odom_to_base_tf"',
        'DeclareLaunchArgument("enable_ground_constraint_in_slam"',
        'DeclareLaunchArgument("img_mask_top"',
        'DeclareLaunchArgument("img_mask_bottom"',
        'DeclareLaunchArgument("img_mask_left"',
        'DeclareLaunchArgument("img_mask_right"',
        'DeclareLaunchArgument("imu_jitter_threshold_ms"',
        'DeclareLaunchArgument("enable_slam_visualization"',
    ):
        assert removed_text not in launch_text
