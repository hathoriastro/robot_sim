from launch import LaunchDescription

from launch.actions import ExecuteProcess


def generate_launch_description():

    gazebo = ExecuteProcess(
        cmd=[
            'gz',
            'sim',
            '-r',
            'worlds/empty.sdf'
        ],
        output='screen'
    )

    return LaunchDescription([
        gazebo
    ])