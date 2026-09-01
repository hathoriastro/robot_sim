"""Setup script for the robot_sim package."""

import os
from glob import glob

from setuptools import find_packages, setup

package_name = 'robot_sim'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch',
            glob(os.path.join('launch', '*.launch.py'))),
        ('share/' + package_name + '/worlds',
            glob(os.path.join('worlds', '*.sdf'))),
        ('share/' + package_name + '/models',
            glob(os.path.join('models', '*.sdf'))),
        ('share/' + package_name + '/rviz',
            glob(os.path.join('rviz', '*.rviz'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='astro',
    maintainer_email='ahmadtovichha@gmail.com',
    description='Time Attack Waypoint Chaser Robot Simulation',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'keyboard_teleop = robot_sim.keyboard_teleop:main',
            'time_attack_master_node = robot_sim.time_attack_master_node:main',
        ],
    },
)
