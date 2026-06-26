from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    zed_camera = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [
                    FindPackageShare("zed_wrapper"),
                    "launch",
                    "zed_camera.launch.py",
                ]
            )
        ),
        launch_arguments={
            "camera_model": "zed2i",
            "publish_tf": "true",
            "publish_map_tf": "false",
            "publish_imu_tf": "true",
            "ros_params_override_path": PathJoinSubstitution(
                [
                    FindPackageShare("camera_odom_rtabmap_examples"),
                    "config",
                    "zed2i_rtabmap_stereo.yaml",
                ]
            ),
        }.items(),
    )

    stereo_remappings = [
        ("left/image_rect", "/zed/zed_node/left/color/rect/image"),
        ("left/camera_info", "/zed/zed_node/left/color/rect/camera_info"),
        ("right/image_rect", "/zed/zed_node/right/color/rect/image"),
        ("right/camera_info", "/zed/zed_node/right/color/rect/camera_info"),
        ("imu", "/zed/zed_node/imu/data"),
        ("odom", "/odom"),
    ]

    stereo_odometry = Node(
        package="rtabmap_odom",
        executable="stereo_odometry",
        output="screen",
        parameters=[
            {
                "frame_id": "zed_camera_link",
                "subscribe_stereo": True,
                "subscribe_depth": False,
                "approx_sync": True,
                "sync_queue_size": 10,
                "qos": 2,
                "qos_camera_info": 2,
                "qos_imu": 2,
                "wait_imu_to_init": True,
            }
        ],
        remappings=stereo_remappings,
    )

    rtabmap_slam = Node(
        package="rtabmap_slam",
        executable="rtabmap",
        output="screen",
        arguments=["-d"],
        parameters=[
            {
                "frame_id": "zed_camera_link",
                "subscribe_stereo": True,
                "subscribe_depth": False,
                "approx_sync": True,
                "qos": 2,
                "qos_camera_info": 2,
                "qos_odom": 2,
                "qos_imu": 2,
                "wait_imu_to_init": True,
                "subscribe_odom_info": True,
            }
        ],
        remappings=stereo_remappings,
    )

    rviz = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        arguments=[
            "-d",
            PathJoinSubstitution(
                [
                    FindPackageShare("camera_odom_rtabmap_examples"),
                    "rviz",
                    "zed2i_rtabmap_stereo_imu.rviz",
                ]
            ),
        ],
        condition=IfCondition(LaunchConfiguration("launch_rviz")),
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("launch_rviz", default_value="true"),
            zed_camera,
            stereo_odometry,
            rtabmap_slam,
            rviz,
        ]
    )
