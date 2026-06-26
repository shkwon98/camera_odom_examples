cmake_minimum_required(VERSION 3.8)
project(camera_odom_rtabmap_examples)

find_package(ament_cmake REQUIRED)

install(DIRECTORY launch rviz DESTINATION share/${PROJECT_NAME})
install(PROGRAMS
        scripts/restamp_realsense_rgbd.py
        scripts/restamp_realsense_stereo.py
        DESTINATION lib/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(test_realsense_d405_rtabmap_rgbd_launch
                        test/test_realsense_d405_rtabmap_rgbd_launch.py)
  ament_add_pytest_test(test_realsense_d555_rtabmap_rgbd_launch
                        test/test_realsense_d555_rtabmap_rgbd_launch.py)
  ament_add_pytest_test(test_realsense_d555_rtabmap_rgbd_imu_launch
                        test/test_realsense_d555_rtabmap_rgbd_imu_launch.py)
  ament_add_pytest_test(test_realsense_stereo_launches
                        test/test_realsense_stereo_launches.py)
endif()

ament_package()
