import importlib.util
import os
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


def _assert_common_stereo_launch(
    launch_name: str,
    rviz_name: str,
    device_type: str,
    expected_left_topic: str,
    expected_right_topic: str,
):
    launch_file = PACKAGE_ROOT / "launch" / launch_name
    assert launch_file.is_file()
    launch_text = launch_file.read_text()
    entities = _load_launch(launch_file).entities

    argument_names = [
        entity.name
        for entity in entities
        if isinstance(entity, DeclareLaunchArgument)
    ]

    assert argument_names == ["launch_rviz"]
    assert sum(isinstance(entity, IncludeLaunchDescription) for entity in entities) == 0
    assert any(
        isinstance(entity, Node)
        and entity.node_package == "realsense2_camera"
        and entity.node_executable == "realsense2_camera_node"
        for entity in entities
    )
    assert any(
        isinstance(entity, Node)
        and entity.node_package == "rtabmap_odom"
        and entity.node_executable == "stereo_odometry"
        for entity in entities
    )
    assert any(
        isinstance(entity, Node)
        and entity.node_package == "rtabmap_slam"
        and entity.node_executable == "rtabmap"
        for entity in entities
    )
    assert any(
        isinstance(entity, Node)
        and entity.node_package == "rviz2"
        and entity.node_executable == "rviz2"
        for entity in entities
    )

    for realsense_argument in (
        'namespace="camera"',
        'name="camera"',
        f'"device_type": "{device_type}"',
        '"enable_color": False',
        '"enable_depth": False',
        '"enable_infra": False',
        '"enable_infra1": True',
        '"enable_infra2": True',
        '"align_depth.enable": False',
        '"enable_sync": True',
    ):
        assert realsense_argument in launch_text

    for remapping in (
        f'("left/image_rect", "{expected_left_topic}")',
        f'("right/image_rect", "{expected_right_topic}")',
        '("left/camera_info",',
        '("right/camera_info",',
        '("odom", "/odom")',
    ):
        assert remapping in launch_text

    for parameter in (
        '"frame_id": "camera_link"',
        '"subscribe_stereo": True',
        '"subscribe_depth": False',
        '"sync_queue_size": 10',
        '"qos": 2',
        '"qos_image": 2',
        '"qos_camera_info": 2',
        '"qos_odom": 2',
        '"subscribe_odom_info": True',
        'DeclareLaunchArgument("launch_rviz", default_value="true")',
        'IfCondition(LaunchConfiguration("launch_rviz"))',
        f'"{rviz_name}"',
    ):
        assert parameter in launch_text

    _assert_rviz_config(
        PACKAGE_ROOT / "rviz" / rviz_name,
        (
            "/odom",
            "/mapPath",
            "/odomPath",
            "/mapData",
            "/odom_local_map",
            expected_left_topic,
            expected_right_topic,
        ),
    )

    assert "rgbd_odometry" not in launch_text
    assert "rs_launch.py" not in launch_text
    assert '"-d"' in launch_text
    assert '"/camera/camera/aligned_depth_to_color/image_raw"' not in launch_text

    return launch_text, entities


def test_package_metadata_declares_stereo_launch_tests_and_restamp_script():
    cmake_lists = (PACKAGE_ROOT / "CMakeLists.txt").read_text()
    stereo_restamp = PACKAGE_ROOT / "scripts" / "restamp_realsense_stereo.py"

    assert "test_realsense_stereo_launches" in cmake_lists
    assert "scripts/restamp_realsense_stereo.py" in cmake_lists
    assert stereo_restamp.is_file()
    assert os.access(stereo_restamp, os.X_OK)


def test_d405_stereo_launch_uses_infra_stereo_odometry_without_imu():
    launch_text, entities = _assert_common_stereo_launch(
        "realsense_d405_rtabmap_stereo.launch.py",
        "realsense_d405_rtabmap_stereo.rviz",
        "d405",
        "/camera/camera/infra1/image_rect_raw",
        "/camera/camera/infra2/image_rect_raw",
    )

    assert not any(
        isinstance(entity, Node)
        and entity.node_package == "camera_odom_rtabmap_examples"
        and entity.node_executable == "restamp_realsense_stereo.py"
        for entity in entities
    )
    assert not any(
        isinstance(entity, Node)
        and entity.node_package == "imu_filter_madgwick"
        for entity in entities
    )
    assert '"enable_gyro": False' in launch_text
    assert '"enable_accel": False' in launch_text
    assert '"enable_motion": False' in launch_text
    assert '("imu",' not in launch_text
    assert '"wait_imu_to_init": True' not in launch_text


def test_d555_stereo_launch_restamps_infra_stereo_without_imu():
    launch_text, entities = _assert_common_stereo_launch(
        "realsense_d555_rtabmap_stereo.launch.py",
        "realsense_d555_rtabmap_stereo.rviz",
        "d555",
        "/camera_odom_d555/infra1/image_rect_raw",
        "/camera_odom_d555/infra2/image_rect_raw",
    )

    assert any(
        isinstance(entity, Node)
        and entity.node_package == "camera_odom_rtabmap_examples"
        and entity.node_executable == "restamp_realsense_stereo.py"
        for entity in entities
    )
    assert not any(
        isinstance(entity, Node)
        and entity.node_package == "imu_filter_madgwick"
        for entity in entities
    )
    assert '"enable_gyro": False' in launch_text
    assert '"enable_accel": False' in launch_text
    assert '"enable_motion": False' in launch_text
    assert '"left_image_in": "/camera/camera/infra1/image_rect_raw"' in launch_text
    assert '"right_image_in": "/camera/camera/infra2/image_rect_raw"' in launch_text
    assert '"approx_sync": True' in launch_text
    assert '"enable_imu": True' not in launch_text
    assert '("imu",' not in launch_text
    assert '"wait_imu_to_init": True' not in launch_text


def test_d555_stereo_imu_launch_restamps_stereo_and_filtered_imu():
    launch_text, entities = _assert_common_stereo_launch(
        "realsense_d555_rtabmap_stereo_imu.launch.py",
        "realsense_d555_rtabmap_stereo_imu.rviz",
        "d555",
        "/camera_odom_d555/infra1/image_rect_raw",
        "/camera_odom_d555/infra2/image_rect_raw",
    )

    assert any(
        isinstance(entity, Node)
        and entity.node_package == "camera_odom_rtabmap_examples"
        and entity.node_executable == "restamp_realsense_stereo.py"
        for entity in entities
    )
    assert any(
        isinstance(entity, Node)
        and entity.node_package == "imu_filter_madgwick"
        and entity.node_executable == "imu_filter_madgwick_node"
        for entity in entities
    )

    for expected_text in (
        '"enable_gyro": True',
        '"enable_accel": True',
        '"enable_motion": True',
        '"unite_imu_method": 2',
        '"enable_imu": True',
        '"imu_in": "/camera_odom_d555/imu/data_filtered"',
        '"imu_out": "/camera_odom_d555/imu/data"',
        '"use_mag": False',
        '"world_frame": "enu"',
        '"publish_tf": False',
        '"approx_sync": True',
        '("imu/data_raw", "/camera/camera/imu")',
        '("imu/data", "/camera_odom_d555/imu/data_filtered")',
        '("imu", "/camera_odom_d555/imu/data")',
        '"qos_imu": 2',
        '"wait_imu_to_init": True',
    ):
        assert expected_text in launch_text
