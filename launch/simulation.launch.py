"""Launch Gazebo simulation, ROS bridge, master node, and RViz2."""

import glob
import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource

from launch_ros.actions import Node

# Ensure ROS 2 Gazebo vendor binaries, libraries, configs are in environment
for bin_dir in glob.glob('/opt/ros/*/opt/*/bin'):
    if bin_dir not in os.environ.get('PATH', ''):
        os.environ['PATH'] = f"{bin_dir}:{os.environ.get('PATH', '')}"

for lib_dir in glob.glob('/opt/ros/*/opt/*/lib'):
    if lib_dir not in os.environ.get('LD_LIBRARY_PATH', ''):
        os.environ['LD_LIBRARY_PATH'] = (
            f"{lib_dir}:{os.environ.get('LD_LIBRARY_PATH', '')}"
        )

vendor_gz_shares = [
    p for p in glob.glob('/opt/ros/*/opt/*/share/gz') if os.path.isdir(p)
]
existing_gz_config = os.environ.get('GZ_CONFIG_PATH', '')
new_gz_configs = [p for p in vendor_gz_shares if p not in existing_gz_config]
if new_gz_configs:
    all_configs = new_gz_configs + (
        [existing_gz_config] if existing_gz_config else []
    )
    os.environ['GZ_CONFIG_PATH'] = ':'.join(all_configs)


def generate_launch_description():
    """Generate launch description with all simulation and game nodes."""
    pkg_robot_sim = get_package_share_directory('robot_sim')
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')

    world_path = os.path.join(pkg_robot_sim, 'worlds', 'empty.sdf')
    robot_model_path = os.path.join(pkg_robot_sim, 'models', 'robot.sdf')
    rviz_config_path = os.path.join(pkg_robot_sim, 'rviz', 'game_view.rviz')

    # Gazebo Sim launch
    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={'gz_args': f'-r {world_path}'}.items(),
    )

    # Spawn robot model
    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-name', 'my_robot',
            '-file', robot_model_path,
            '-z', '0.05',
        ],
        output='screen',
    )

    # ROS <-> Gazebo Bridge
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist',
            '/odom@nav_msgs/msg/Odometry@gz.msgs.Odometry',
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
            '/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V',
        ],
        output='screen',
    )

    # Game Master Node (Score, Timer, Waypoints, Autopilot PID, RViz 3D HUD)
    master_node = Node(
        package='robot_sim',
        executable='time_attack_master_node',
        output='screen',
    )

    # RViz2 Node
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        arguments=['-d', rviz_config_path],
        output='screen',
    )

    return LaunchDescription([
        gz_sim,
        spawn_robot,
        bridge,
        master_node,
        rviz_node,
    ])
