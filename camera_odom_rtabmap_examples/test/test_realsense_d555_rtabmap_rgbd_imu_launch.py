import importlib.util
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


def test_package_metadata_declares_d555_rtabmap_rgbd_imu_test():
    package_xml = (PACKAGE_ROOT / "package.xml").read_text()
    cmake_lists = (PACKAGE_ROOT / "CMakeLists.txt").read_text()

    assert "<exec_depend>imu_filter_madgwick</exec_depend>" in package_xml
    assert "test_realsense_d555_rtabmap_rgbd_imu_launch" in cmake_lists


def test_d555_rtabmap_rgbd_imu_launch_composes_realsense_imu_odometry_and_slam():
    launch_file = PACKAGE_ROOT / "launch" / "realsense_d555_rtabmap_rgbd_imu.launch.py"
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
        and entity.node_package == "imu_filter_madgwick"
        and entity.node_executable == "imu_filter_madgwick_node"
        for entity in entities
    )
    assert any(
        isinstance(entity, Node)
        and entity.node_package == "camera_odom_rtabmap_examples"
        and entity.node_executable == "restamp_realsense_rgbd.py"
        for entity in entities
    )
    assert any(
        isinstance(entity, Node)
        and entity.node_package == "rtabmap_odom"
        and entity.node_executable == "rgbd_odometry"
        for entity in entities
    )
    assert any(
        isinstance(entity, Node)
        and entity.node_package == "rtabmap_sync"
        and entity.node_executable == "rgbd_sync"
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
        '"device_type": "d555"',
        '"enable_infra": False',
        '"enable_infra1": False',
        '"enable_infra2": False',
        '"enable_gyro": True',
        '"enable_accel": True',
        '"enable_motion": True',
        '"unite_imu_method": 2',
        '"align_depth.enable": False',
        '"enable_sync": True',
        '"rgb_camera.color_profile": "640,360,30"',
        '"depth_module.depth_profile": "640,360,30"',
    ):
        assert realsense_argument in launch_text

    for imu_filter_argument in (
        '"use_mag": False',
        '"world_frame": "enu"',
        '"publish_tf": False',
        '("imu/data_raw", "/camera/camera/imu")',
        '("imu/data", "/camera_odom_d555/imu/data_filtered")',
    ):
        assert imu_filter_argument in launch_text

    for restamp_argument in (
        '"enable_imu": True',
        '"imu_in": "/camera_odom_d555/imu/data_filtered"',
        '"imu_out": "/camera_odom_d555/imu/data"',
    ):
        assert restamp_argument in launch_text

    restamp_script = PACKAGE_ROOT / "scripts" / "restamp_realsense_rgbd.py"
    restamp_text = restamp_script.read_text()
    for expected_text in (
        "from sensor_msgs.msg import Imu",
        'self.declare_parameter("enable_imu", False)',
        "Imu,",
    ):
        assert expected_text in restamp_text

    for remapping in (
        '("rgb/image", "/camera_odom_d555/color/image_raw")',
        '("depth/image", "/camera_odom_d555/depth/image_rect_raw")',
        '("rgb/camera_info", "/camera_odom_d555/color/camera_info")',
        '("rgbd_image", "/camera_odom_d555/rgbd_image")',
        '("imu", "/camera_odom_d555/imu/data")',
        '("odom", "/odom")',
    ):
        assert remapping in launch_text

    for parameter in (
        '"frame_id": "camera_link"',
        '"subscribe_rgbd": True',
        '"approx_sync": True',
        '"sync_queue_size": 10',
        '"qos": 2',
        '"qos_image": 2',
        '"qos_camera_info": 2',
        '"qos_odom": 2',
        '"qos_imu": 2',
        '"wait_imu_to_init": True',
        '"subscribe_odom_info": True',
        'DeclareLaunchArgument("launch_rviz", default_value="true")',
        'IfCondition(LaunchConfiguration("launch_rviz"))',
        '"realsense_d555_rtabmap_rgbd_imu.rviz"',
    ):
        assert parameter in launch_text

    _assert_rviz_config(
        PACKAGE_ROOT / "rviz" / "realsense_d555_rtabmap_rgbd_imu.rviz",
        (
            "/odom",
            "/mapPath",
            "/odomPath",
            "/mapData",
            "/odom_local_map",
            "/camera_odom_d555/color/image_raw",
            "/camera_odom_d555/depth/image_rect_raw",
        ),
    )

    assert "rs_launch.py" not in launch_text
    assert '"-d"' in launch_text

    for removed_argument in (
        "odometry_parameters =",
        "slam_parameters =",
        '"align_depth.enable": True',
        '"/camera/camera/aligned_depth_to_color/image_raw"',
        '"/camera_odom_d555/aligned_depth_to_color/image_raw"',
    ):
        assert removed_argument not in launch_text
