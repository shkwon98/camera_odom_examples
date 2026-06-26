from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import ComposableNodeContainer, Node
from launch_ros.descriptions import ComposableNode
from launch_ros.substitutions import FindPackageShare


def _launch_setup(context, *args, **kwargs):
    depth_profile = LaunchConfiguration("depth_profile")
    color_profile = LaunchConfiguration("color_profile")
    image_jitter_threshold_ms = LaunchConfiguration("image_jitter_threshold_ms")
    sync_matching_threshold_ms = LaunchConfiguration("sync_matching_threshold_ms")

    realsense_camera = Node(
        name="camera",
        namespace="",
        package="realsense2_camera",
        executable="realsense2_camera_node",
        output="screen",
        parameters=[
            {
                "device_type": "d555",
                "enable_infra": False,
                "enable_infra1": False,
                "enable_infra2": False,
                "enable_gyro": False,
                "enable_accel": False,
                "enable_motion": False,
                "align_depth.enable": True,
                "enable_sync": True,
                "depth_module.emitter_enabled": True,
                "depth_module.depth_profile": depth_profile,
                "rgb_camera.color_profile": color_profile,
            }
        ],
    )

    restamp_rgbd = Node(
        package="camera_odom_isaac_ros_examples",
        executable="restamp_realsense_rgbd.py",
        name="restamp_realsense_rgbd",
        output="screen",
        parameters=[
            {
                "color_image_in": "/camera/color/image_raw",
                "color_image_out": "/camera_odom_d555/color/image_raw",
                "depth_image_in": "/camera/aligned_depth_to_color/image_raw",
                "depth_image_out": "/camera_odom_d555/aligned_depth_to_color/image_raw",
                "color_info_in": "/camera/color/camera_info",
                "color_info_out": "/camera_odom_d555/color/camera_info",
            }
        ],
    )

    visual_slam = ComposableNode(
        package="isaac_ros_visual_slam",
        plugin="nvidia::isaac_ros::visual_slam::VisualSlamNode",
        name="visual_slam_node",
        parameters=[
            {
                "tracking_mode": 2,
                "depth_scale_factor": 1000.0,
                "rectified_images": False,
                "image_jitter_threshold_ms": image_jitter_threshold_ms,
                "sync_matching_threshold_ms": sync_matching_threshold_ms,
                "base_frame": "camera_link",
                "camera_optical_frames": ["camera_color_optical_frame"],
                "enable_slam_visualization": False,
                "enable_landmarks_view": False,
                "enable_observations_view": False,
                "enable_localization_n_mapping": False,
                "publish_map_to_odom_tf": False,
                "publish_odom_to_base_tf": True,
                "min_num_images": 1,
                "num_cameras": 1,
                "depth_camera_id": 0,
            }
        ],
        remappings=[
            ("visual_slam/image_0", "/camera_odom_d555/color/image_raw"),
            ("visual_slam/camera_info_0", "/camera_odom_d555/color/camera_info"),
            ("visual_slam/depth_0", "/camera_odom_d555/aligned_depth_to_color/image_raw"),
        ],
    )

    visual_slam_container = ComposableNodeContainer(
        package="rclcpp_components",
        executable="component_container_mt",
        name="realsense_d555_visual_slam_container",
        namespace="",
        composable_node_descriptions=[visual_slam],
        output="screen",
    )

    return [realsense_camera, restamp_rgbd, visual_slam_container]


def generate_launch_description():
    rviz = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        arguments=[
            "-d",
            PathJoinSubstitution(
                [
                    FindPackageShare("camera_odom_isaac_ros_examples"),
                    "rviz",
                    "realsense_d555_visual_slam.rviz",
                ]
            ),
        ],
        condition=IfCondition(LaunchConfiguration("launch_rviz")),
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("depth_profile", default_value="640,360,30"),
            DeclareLaunchArgument("color_profile", default_value="640,360,30"),
            DeclareLaunchArgument("image_jitter_threshold_ms", default_value="34.0"),
            DeclareLaunchArgument("sync_matching_threshold_ms", default_value="10.0"),
            DeclareLaunchArgument("launch_rviz", default_value="true"),
            OpaqueFunction(function=_launch_setup),
            rviz,
        ]
    )
