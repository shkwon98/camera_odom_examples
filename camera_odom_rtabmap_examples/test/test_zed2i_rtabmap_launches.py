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
        "Reliability Policy: Best Effort",
        "Class: rviz_default_plugins/Image",
    ):
        assert expected_text in rviz_text
    assert "Shape: Axes" not in rviz_text
    for topic in expected_topics:
        assert topic in rviz_text


def _assert_common_zed_launch(
    launch_name: str,
    rviz_name: str,
    odometry_executable: str,
    expected_topics: tuple[str, ...],
    publish_tf: str = "false",
    publish_imu_tf: str | None = None,
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
    assert any(isinstance(entity, IncludeLaunchDescription) for entity in entities)
    assert any(
        isinstance(entity, Node)
        and entity.node_package == "rtabmap_odom"
        and entity.node_executable == odometry_executable
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

    for expected_text in (
        'FindPackageShare("zed_wrapper")',
        '"zed_camera.launch.py"',
        '"camera_model": "zed2i"',
        f'"publish_tf": "{publish_tf}"',
        '"publish_map_tf": "false"',
        '"frame_id": "zed_camera_link"',
        '"sync_queue_size": 10',
        '"qos": 2',
        '"qos_camera_info": 2',
        '"qos_odom": 2',
        'DeclareLaunchArgument("launch_rviz", default_value="true")',
        'IfCondition(LaunchConfiguration("launch_rviz"))',
        f'"{rviz_name}"',
        '"-d"',
    ):
        assert expected_text in launch_text
    if publish_imu_tf is not None:
        assert f'"publish_imu_tf": "{publish_imu_tf}"' in launch_text

    _assert_rviz_config(
        PACKAGE_ROOT / "rviz" / rviz_name,
        (
            "/odom",
            "/mapPath",
            "/odomPath",
            "/mapData",
            "/odom_local_map",
            *expected_topics,
        ),
    )

    return launch_text, entities


def test_package_metadata_declares_zed2i_rtabmap_tests_and_dependencies():
    package_xml = (PACKAGE_ROOT / "package.xml").read_text()
    cmake_lists = (PACKAGE_ROOT / "CMakeLists.txt").read_text()

    assert "<exec_depend>rtabmap_sync</exec_depend>" in package_xml
    assert "<exec_depend>zed_wrapper</exec_depend>" in package_xml
    assert "install(DIRECTORY launch rviz config" in cmake_lists
    assert "test_zed2i_rtabmap_launches" in cmake_lists


def test_zed2i_rgbd_launch_uses_rgbd_sync_and_rgbd_odometry_without_imu():
    launch_text, entities = _assert_common_zed_launch(
        "zed2i_rtabmap_rgbd.launch.py",
        "zed2i_rtabmap_rgbd.rviz",
        "rgbd_odometry",
        (
            "/zed/zed_node/rgb/color/rect/image",
            "/zed/zed_node/depth/depth_registered",
        ),
    )

    assert any(
        isinstance(entity, Node)
        and entity.node_package == "rtabmap_sync"
        and entity.node_executable == "rgbd_sync"
        for entity in entities
    )
    for expected_text in (
        '("rgb/image", "/zed/zed_node/rgb/color/rect/image")',
        '("rgb/camera_info", "/zed/zed_node/rgb/color/rect/camera_info")',
        '("depth/image", "/zed/zed_node/depth/depth_registered")',
        '("rgbd_image", "/camera_odom_zed2i/rgbd_image")',
        '"ros_params_override_path": PathJoinSubstitution',
        '"zed2i_rtabmap_rgbd.yaml"',
        '"subscribe_rgbd": True',
        '"approx_sync": True',
    ):
        assert expected_text in launch_text
    assert '("imu",' not in launch_text
    assert '"wait_imu_to_init": True' not in launch_text


def test_zed2i_rgbd_imu_launch_uses_zed_imu_with_rgbd_odometry():
    launch_text, entities = _assert_common_zed_launch(
        "zed2i_rtabmap_rgbd_imu.launch.py",
        "zed2i_rtabmap_rgbd_imu.rviz",
        "rgbd_odometry",
        (
            "/zed/zed_node/rgb/color/rect/image",
            "/zed/zed_node/depth/depth_registered",
        ),
        publish_tf="true",
        publish_imu_tf="true",
    )

    assert any(
        isinstance(entity, Node)
        and entity.node_package == "rtabmap_sync"
        and entity.node_executable == "rgbd_sync"
        for entity in entities
    )
    for expected_text in (
        '("rgb/image", "/zed/zed_node/rgb/color/rect/image")',
        '("rgb/camera_info", "/zed/zed_node/rgb/color/rect/camera_info")',
        '("rgbd_image", "/camera_odom_zed2i/rgbd_image")',
        '("imu", "/zed/zed_node/imu/data")',
        '"ros_params_override_path": PathJoinSubstitution',
        '"zed2i_rtabmap_rgbd.yaml"',
        '"subscribe_rgbd": True',
        '"approx_sync": True',
        '"qos_imu": 2',
        '"wait_imu_to_init": True',
    ):
        assert expected_text in launch_text


def test_zed2i_stereo_launch_uses_left_right_stereo_odometry_without_imu():
    launch_text, entities = _assert_common_zed_launch(
        "zed2i_rtabmap_stereo.launch.py",
        "zed2i_rtabmap_stereo.rviz",
        "stereo_odometry",
        (
            "/zed/zed_node/left/color/rect/image",
            "/zed/zed_node/right/color/rect/image",
        ),
    )

    assert not any(
        isinstance(entity, Node)
        and entity.node_package == "rtabmap_sync"
        for entity in entities
    )
    for expected_text in (
        '("left/image_rect", "/zed/zed_node/left/color/rect/image")',
        '("left/camera_info", "/zed/zed_node/left/color/rect/camera_info")',
        '("right/image_rect", "/zed/zed_node/right/color/rect/image")',
        '("right/camera_info", "/zed/zed_node/right/color/rect/camera_info")',
        '"ros_params_override_path": PathJoinSubstitution',
        '"zed2i_rtabmap_stereo.yaml"',
        '"subscribe_stereo": True',
        '"subscribe_depth": False',
        '"approx_sync": True',
    ):
        assert expected_text in launch_text
    assert '("imu",' not in launch_text
    assert '"wait_imu_to_init": True' not in launch_text


def test_zed2i_stereo_imu_launch_uses_zed_imu_with_stereo_odometry():
    launch_text, entities = _assert_common_zed_launch(
        "zed2i_rtabmap_stereo_imu.launch.py",
        "zed2i_rtabmap_stereo_imu.rviz",
        "stereo_odometry",
        (
            "/zed/zed_node/left/color/rect/image",
            "/zed/zed_node/right/color/rect/image",
        ),
        publish_tf="true",
        publish_imu_tf="true",
    )

    assert not any(
        isinstance(entity, Node)
        and entity.node_package == "rtabmap_sync"
        for entity in entities
    )
    for expected_text in (
        '("left/image_rect", "/zed/zed_node/left/color/rect/image")',
        '("right/image_rect", "/zed/zed_node/right/color/rect/image")',
        '"ros_params_override_path": PathJoinSubstitution',
        '"zed2i_rtabmap_stereo.yaml"',
        '("imu", "/zed/zed_node/imu/data")',
        '"subscribe_stereo": True',
        '"subscribe_depth": False',
        '"approx_sync": True',
        '"qos_imu": 2',
        '"wait_imu_to_init": True',
    ):
        assert expected_text in launch_text
