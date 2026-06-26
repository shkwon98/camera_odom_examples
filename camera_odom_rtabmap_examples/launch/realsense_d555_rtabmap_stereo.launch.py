from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    realsense_camera = Node(
        package="realsense2_camera",
        executable="realsense2_camera_node",
        namespace="camera",
        name="camera",
        output="screen",
        parameters=[
            {
                "camera_name": "camera",
                "camera_namespace": "camera",
                "device_type": "d555",
                "enable_color": False,
                "enable_depth": False,
                "enable_infra": False,
                "enable_infra1": True,
                "enable_infra2": True,
                "enable_gyro": False,
                "enable_accel": False,
                "enable_motion": False,
                "align_depth.enable": False,
                "enable_sync": True,
            }
        ],
    )

    restamp_stereo = Node(
        package="camera_odom_rtabmap_examples",
        executable="restamp_realsense_stereo.py",
        name="restamp_realsense_stereo",
        output="screen",
        parameters=[
            {
                "left_image_in": "/camera/camera/infra1/image_rect_raw",
                "left_image_out": "/camera_odom_d555/infra1/image_rect_raw",
                "left_info_in": "/camera/camera/infra1/camera_info",
                "left_info_out": "/camera_odom_d555/infra1/camera_info",
                "right_image_in": "/camera/camera/infra2/image_rect_raw",
                "right_image_out": "/camera_odom_d555/infra2/image_rect_raw",
                "right_info_in": "/camera/camera/infra2/camera_info",
                "right_info_out": "/camera_odom_d555/infra2/camera_info",
            }
        ],
    )

    stereo_remappings = [
        ("left/image_rect", "/camera_odom_d555/infra1/image_rect_raw"),
        ("left/camera_info", "/camera_odom_d555/infra1/camera_info"),
        ("right/image_rect", "/camera_odom_d555/infra2/image_rect_raw"),
        ("right/camera_info", "/camera_odom_d555/infra2/camera_info"),
        ("odom", "/odom"),
    ]

    stereo_odometry = Node(
        package="rtabmap_odom",
        executable="stereo_odometry",
        output="screen",
        parameters=[
            {
                "frame_id": "camera_link",
                "subscribe_stereo": True,
                "approx_sync": True,
                "sync_queue_size": 10,
                "qos": 2,
                "qos_camera_info": 2,
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
                "frame_id": "camera_link",
                "subscribe_stereo": True,
                "subscribe_depth": False,
                "approx_sync": True,
                "qos_image": 2,
                "qos_camera_info": 2,
                "qos_odom": 2,
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
                    "realsense_d555_rtabmap_stereo.rviz",
                ]
            ),
        ],
        condition=IfCondition(LaunchConfiguration("launch_rviz")),
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("launch_rviz", default_value="true"),
            realsense_camera,
            restamp_stereo,
            stereo_odometry,
            rtabmap_slam,
            rviz,
        ]
    )
