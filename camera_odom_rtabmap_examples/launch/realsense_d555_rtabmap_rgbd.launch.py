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
                "enable_infra": False,
                "enable_infra1": False,
                "enable_infra2": False,
                "enable_gyro": False,
                "enable_accel": False,
                "enable_motion": False,
                "align_depth.enable": False,
                "enable_sync": True,
                "rgb_camera.color_profile": "640,360,30",
                "depth_module.depth_profile": "640,360,30",
            }
        ],
    )

    restamp_rgbd = Node(
        package="camera_odom_rtabmap_examples",
        executable="restamp_realsense_rgbd.py",
        name="restamp_realsense_rgbd",
        output="screen",
        parameters=[
            {
                "color_image_in": "/camera/camera/color/image_raw",
                "color_image_out": "/camera_odom_d555/color/image_raw",
                "depth_image_in": "/camera/camera/depth/image_rect_raw",
                "depth_image_out": "/camera_odom_d555/depth/image_rect_raw",
                "color_info_in": "/camera/camera/color/camera_info",
                "color_info_out": "/camera_odom_d555/color/camera_info",
            }
        ],
    )

    rgbd_remappings = [
        ("rgb/image", "/camera_odom_d555/color/image_raw"),
        ("depth/image", "/camera_odom_d555/depth/image_rect_raw"),
        ("rgb/camera_info", "/camera_odom_d555/color/camera_info"),
        ("odom", "/odom"),
    ]

    rgbd_odometry = Node(
        package="rtabmap_odom",
        executable="rgbd_odometry",
        output="screen",
        parameters=[
            {
                "frame_id": "camera_link",
                "odom_frame_id": "odom",
                "publish_tf": True,
                "approx_sync": True,
                "topic_queue_size": 10,
                "sync_queue_size": 10,
                "qos": 2,
                "qos_camera_info": 2,
                "subscribe_depth": True,
            }
        ],
        remappings=rgbd_remappings,
    )

    rtabmap_slam = Node(
        package="rtabmap_slam",
        executable="rtabmap",
        output="screen",
        arguments=["-d"],
        parameters=[
            {
                "frame_id": "camera_link",
                "map_frame_id": "map",
                "publish_tf": True,
                "approx_sync": True,
                "topic_queue_size": 10,
                "sync_queue_size": 10,
                "qos_image": 2,
                "qos_camera_info": 2,
                "qos_odom": 2,
                "subscribe_depth": True,
                "subscribe_odom_info": True,
            }
        ],
        remappings=rgbd_remappings,
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
                    "realsense_d555_rtabmap_rgbd.rviz",
                ]
            ),
        ],
        condition=IfCondition(LaunchConfiguration("launch_rviz")),
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("launch_rviz", default_value="true"),
            realsense_camera,
            restamp_rgbd,
            rgbd_odometry,
            rtabmap_slam,
            rviz,
        ]
    )
