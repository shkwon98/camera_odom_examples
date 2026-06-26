cmake_minimum_required(VERSION 3.8)
project(camera_odom_isaac_ros_examples)

find_package(ament_cmake REQUIRED)

install(DIRECTORY config launch rviz DESTINATION share/${PROJECT_NAME})
install(PROGRAMS scripts/restamp_realsense_rgbd.py
        DESTINATION lib/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(test_zed2i_visual_slam_launch
                        test/test_zed2i_visual_slam_launch.py)
  ament_add_pytest_test(test_realsense_d405_visual_slam_launch
                        test/test_realsense_d405_visual_slam_launch.py)
  ament_add_pytest_test(test_realsense_d555_visual_slam_launch
                        test/test_realsense_d555_visual_slam_launch.py)
endif()

ament_package()
