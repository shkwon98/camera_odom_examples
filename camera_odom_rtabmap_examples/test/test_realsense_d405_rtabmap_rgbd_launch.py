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


def test_package_metadata_installs_launch_files():
    package_xml = (PACKAGE_ROOT / "package.xml").read_text()
    cmake_lists = (PACKAGE_ROOT / "CMakeLists.txt").read_text()

    assert "<name>camera_odom_rtabmap_examples</name>" in package_xml
    assert "project(camera_odom_rtabmap_examples)" in cmake_lists
    for dependency in (
        "launch",
        "launch_ros",
        "realsense2_camera",
        "rtabmap_odom",
        "rtabmap_slam",
        "rtabmap_sync",
        "rclpy",
        "sensor_msgs",
        "rviz2",
    ):
        assert f"<exec_depend>{dependency}</exec_depend>" in package_xml

    assert "install(DIRECTORY launch rviz config DESTINATION share/${PROJECT_NAME})" in cmake_lists
    assert "install(PROGRAMS" in cmake_lists
    assert "scripts/restamp_realsense_rgbd.py" in cmake_lists
    assert "scripts/restamp_realsense_stereo.py" in cmake_lists


def test_d405_rtabmap_rgbd_launch_composes_realsense_odometry_and_slam():
    launch_file = PACKAGE_ROOT / "launch" / "realsense_d405_rtabmap_rgbd.launch.py"
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
        '"device_type": "d405"',
        '"enable_infra": False',
        '"enable_infra1": False',
        '"enable_infra2": False',
        '"enable_gyro": False',
        '"enable_accel": False',
        '"enable_motion": False',
        '"align_depth.enable": False',
        '"enable_sync": True',
        '"rgb_camera.color_profile": "640,480,60"',
        '"depth_module.depth_profile": "640,480,60"',
    ):
        assert realsense_argument in launch_text

    for remapping in (
        '("rgb/image", "/camera/camera/color/image_raw")',
        '("depth/image", "/camera/camera/depth/image_rect_raw")',
        '("rgb/camera_info", "/camera/camera/color/camera_info")',
        '("rgbd_image", "/camera_odom_d405/rgbd_image")',
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
        '"subscribe_odom_info": True',
        'DeclareLaunchArgument("launch_rviz", default_value="true")',
        'IfCondition(LaunchConfiguration("launch_rviz"))',
        '"realsense_d405_rtabmap_rgbd.rviz"',
    ):
        assert parameter in launch_text

    _assert_rviz_config(
        PACKAGE_ROOT / "rviz" / "realsense_d405_rtabmap_rgbd.rviz",
        (
            "/odom",
            "/mapPath",
            "/odomPath",
            "/mapData",
            "/odom_local_map",
            "/camera/camera/color/image_raw",
            "/camera/camera/depth/image_rect_raw",
        ),
    )

    assert "rs_launch.py" not in launch_text
    assert '"-d"' in launch_text
    for removed_argument in (
        "realsense_rtabmap_rgbd.launch.py",
        '"initial_reset"',
        'DeclareLaunchArgument("camera_name"',
        'DeclareLaunchArgument("camera_namespace"',
        '"enable_color": "true"',
        '"enable_depth": "true"',
        '"enable_infra": "false"',
        '"enable_infra1": "false"',
        '"enable_infra2": "false"',
        '"enable_gyro": "false"',
        '"enable_accel": "false"',
        '"enable_motion": "false"',
        '"enable_rgbd": "true"',
        "rgb_camera_profile",
        "depth_module_profile",
        "align_depth_enable",
        "depth_module.emitter_enabled",
        "depth_module_emitter_enabled",
        'LaunchConfiguration("enable_sync")',
        'LaunchConfiguration("enable_rgbd")',
        'LaunchConfiguration("depth_qos")',
        'LaunchConfiguration("color_qos")',
        'LaunchConfiguration("frame_id")',
        'LaunchConfiguration("odom_frame_id")',
        'LaunchConfiguration("map_frame_id")',
        'LaunchConfiguration("publish_tf")',
        'DeclareLaunchArgument("enable_sync"',
        'DeclareLaunchArgument("enable_rgbd"',
        'DeclareLaunchArgument("rgb_camera_profile"',
        'DeclareLaunchArgument("depth_module_profile"',
        'DeclareLaunchArgument("depth_qos"',
        'DeclareLaunchArgument("color_qos"',
        'DeclareLaunchArgument("frame_id"',
        'DeclareLaunchArgument("odom_frame_id"',
        'DeclareLaunchArgument("map_frame_id"',
        'DeclareLaunchArgument("publish_tf"',
        '"odom_frame_id": "odom"',
        '"map_frame_id": "map"',
        '"publish_tf": True',
        '"topic_queue_size": 10',
        '"subscribe_depth": True',
        '"/camera/camera/aligned_depth_to_color/image_raw"',
    ):
        assert removed_argument not in launch_text

    assert "delete_db_on_start" not in launch_text
    assert "def rtabmap_slam_node" not in launch_text
    assert "UnlessCondition" not in launch_text
