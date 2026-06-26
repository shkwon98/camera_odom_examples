import json
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.conditions import IfCondition
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import ComposableNodeContainer, Node
from launch_ros.descriptions import ComposableNode
from launch_ros.substitutions import FindPackageShare


def _load_specs(context):
    specs_file = LaunchConfiguration("interface_specs_file").perform(context)
    with open(specs_file, "r", encoding="utf-8") as file:
        return json.load(file)


def _image_converter(name, encoding, width, height, input_topic, output_topic):
    return ComposableNode(
        package="isaac_ros_image_proc",
        plugin="nvidia::isaac_ros::image_proc::ImageFormatConverterNode",
        name=name,
        parameters=[
            {
                "encoding_desired": encoding,
                "image_width": width,
                "image_height": height,
            }
        ],
        remappings=[
            ("image_raw", input_topic),
            ("image", output_topic),
        ],
    )


def _launch_setup(context, *args, **kwargs):
    specs = _load_specs(context)
    width = specs["camera_resolution"]["width"]
    height = specs["camera_resolution"]["height"]
    camera_model = specs["camera_model"]

    pub_frame_rate = LaunchConfiguration("pub_frame_rate")
    grab_frame_rate = LaunchConfiguration("grab_frame_rate")
    grab_resolution = LaunchConfiguration("grab_resolution")
    sync_matching_threshold_ms = LaunchConfiguration("sync_matching_threshold_ms")
    image_jitter_threshold_ms = LaunchConfiguration("image_jitter_threshold_ms")

    zed_wrapper_share = get_package_share_directory("zed_wrapper")
    zed_common_config = os.path.join(zed_wrapper_share, "config", "common_stereo.yaml")
    zed_camera_config = os.path.join(zed_wrapper_share, "config", f"{camera_model}.yaml")
    zed_description_xacro = os.path.join(
        get_package_share_directory("zed_description"),
        "urdf",
        "zed_descr.urdf.xacro",
    )

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="zed_state_publisher",
        output="screen",
        parameters=[
            {
                "robot_description": Command(
                    [
                        "xacro ",
                        zed_description_xacro,
                        " camera_name:=",
                        camera_model,
                        " camera_model:=",
                        camera_model,
                    ]
                )
            }
        ],
    )

    zed_camera = ComposableNode(
        package="zed_components",
        plugin="stereolabs::ZedCamera",
        name="zed_node",
        parameters=[
            zed_common_config,
            zed_camera_config,
            {
                "general.camera_name": camera_model,
                "general.grab_frame_rate": grab_frame_rate,
                "general.grab_resolution": grab_resolution,
                "general.pub_frame_rate": pub_frame_rate,
                "general.pub_resolution": "NATIVE",
                "video.enable_24bit_output": True,
                "video.publish_left_right": True,
                "video.publish_rgb": False,
                "video.publish_raw": False,
                "video.publish_gray": False,
                "depth.depth_mode": "NONE",
                "depth.publish_depth_map": False,
                "depth.publish_point_cloud": False,
                "pos_tracking.pos_tracking_enabled": False,
                "pos_tracking.publish_tf": False,
                "pos_tracking.publish_map_tf": False,
                "pos_tracking.publish_odom_pose": False,
                "sensors.publish_imu": False,
                "sensors.publish_imu_tf": False,
            },
        ],
        remappings=[
            ("zed_node/left/color/rect/camera_info", "/left/camera_info_rect"),
            ("zed_node/right/color/rect/camera_info", "/right/camera_info_rect"),
        ],
        extra_arguments=[{"use_intra_process_comms": True}],
    )

    visual_slam = ComposableNode(
        package="isaac_ros_visual_slam",
        plugin="nvidia::isaac_ros::visual_slam::VisualSlamNode",
        name="visual_slam_node",
        parameters=[
            {
                "rectified_images": True,
                "enable_slam_visualization": False,
                "enable_landmarks_view": False,
                "enable_observations_view": False,
                "camera_optical_frames": [
                    "zed2i_left_camera_frame_optical",
                    "zed2i_right_camera_frame_optical",
                ],
                "base_frame": "zed2i_camera_center",
                "num_cameras": 2,
                "tracking_mode": 0,
                "enable_localization_n_mapping": False,
                "publish_map_to_odom_tf": False,
                "publish_odom_to_base_tf": True,
                "sync_matching_threshold_ms": sync_matching_threshold_ms,
                "image_jitter_threshold_ms": image_jitter_threshold_ms,
            }
        ],
        remappings=[
            ("/visual_slam/image_0", "left/image_rect_mono"),
            ("/visual_slam/camera_info_0", "left/camera_info_rect"),
            ("/visual_slam/image_1", "right/image_rect_mono"),
            ("/visual_slam/camera_info_1", "right/camera_info_rect"),
        ],
    )

    visual_slam_container = ComposableNodeContainer(
        package="rclcpp_components",
        executable="component_container_mt",
        name="zed2i_visual_slam_container",
        namespace="",
        composable_node_descriptions=[
            zed_camera,
            _image_converter(
                "zed_left_rgb_converter",
                "rgb8",
                width,
                height,
                "zed_node/left/color/rect/image",
                "left/image_rect",
            ),
            _image_converter(
                "zed_right_rgb_converter",
                "rgb8",
                width,
                height,
                "zed_node/right/color/rect/image",
                "right/image_rect",
            ),
            _image_converter(
                "vslam_left_mono_converter",
                "mono8",
                width,
                height,
                "left/image_rect",
                "left/image_rect_mono",
            ),
            _image_converter(
                "vslam_right_mono_converter",
                "mono8",
                width,
                height,
                "right/image_rect",
                "right/image_rect_mono",
            ),
            visual_slam,
        ],
        output="screen",
    )

    return [robot_state_publisher, visual_slam_container]


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
                    "zed2i_visual_slam.rviz",
                ]
            ),
        ],
        condition=IfCondition(LaunchConfiguration("launch_rviz")),
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "interface_specs_file",
                default_value=PathJoinSubstitution(
                    [
                        FindPackageShare("camera_odom_isaac_ros_examples"),
                        "config",
                        "zed2i_visual_slam_interface_specs.json",
                    ]
                ),
            ),
            DeclareLaunchArgument("pub_frame_rate", default_value="30.0"),
            DeclareLaunchArgument("grab_frame_rate", default_value="30"),
            DeclareLaunchArgument("grab_resolution", default_value="VGA"),
            DeclareLaunchArgument("image_jitter_threshold_ms", default_value="34.0"),
            DeclareLaunchArgument("sync_matching_threshold_ms", default_value="5.0"),
            DeclareLaunchArgument("launch_rviz", default_value="true"),
            OpaqueFunction(function=_launch_setup),
            rviz,
        ]
    )
