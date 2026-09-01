"""Keyboard teleoperation node for robot simulation."""

import select
import sys
import termios
import threading
import tty

from geometry_msgs.msg import Twist

import rclpy
from rclpy.node import Node

from std_msgs.msg import String


class KeyboardTeleop(Node):
    """Interactive terminal keyboard teleoperation and game controller node."""

    def __init__(self):
        """Initialize publishers, speeds, and background keyboard thread."""
        super().__init__('keyboard_teleop')

        # Publish manual cmd_vel to /cmd_vel_manual and /cmd_vel
        self.publisher_manual = self.create_publisher(
            Twist,
            '/cmd_vel_manual',
            10
        )
        self.publisher_direct = self.create_publisher(
            Twist,
            '/cmd_vel',
            10
        )

        # Publish game control events (/game_control)
        self.pub_game_control = self.create_publisher(
            String,
            '/game_control',
            10
        )

        self.speed = 0.8
        self.turn_speed = 1.4

        self.key_timeout = 0.1  # seconds
        self.running = True

        # Save terminal settings
        self.settings = termios.tcgetattr(sys.stdin)

        self.print_ui()

        # Start keyboard thread
        self.keyboard_thread = threading.Thread(
            target=self.keyboard_loop,
            daemon=True
        )
        self.keyboard_thread.start()

    def print_ui(self):
        """Print the game controller keyboard keybindings banner."""
        print('\n' + '=' * 60)
        print('   🎮 TIME ATTACK: COIN RUSH - GAME CONTROLLER 🎮')
        print('=' * 60)
        print(' [W / ↑] : Maju          | [S / ↓] : Mundur')
        print(' [A / ←] : Belok Kiri    | [D / →] : Belok Kanan')
        print(' [SPACE] : Stop')
        print(' [M]     : Switch Mode (Manual WASD <--> Autopilot AI)')
        print(' [R]     : Instant Reset Game (New Player / Restart)')
        print(' [CTRL+C]: Keluar')
        print('=' * 60 + '\n')

    def _key_pressed(self, timeout):
        """Check if characters are ready on stdin within given timeout."""
        ready, _, _ = select.select([sys.stdin], [], [], timeout)
        return bool(ready)

    def keyboard_loop(self):
        """Continuously capture non-blocking keystrokes and publish speed."""
        tty.setcbreak(sys.stdin.fileno())

        try:
            last_linear = 0.0
            last_angular = 0.0

            while self.running:
                msg = Twist()

                if self._key_pressed(self.key_timeout):
                    key = sys.stdin.read(1)

                    # WASD keys
                    if key == 'w':
                        msg.linear.x = self.speed
                    elif key == 's':
                        msg.linear.x = -self.speed
                    elif key == 'a':
                        msg.angular.z = self.turn_speed
                    elif key == 'd':
                        msg.angular.z = -self.turn_speed

                    # Arrow keys escape sequence
                    elif key == '\x1b':
                        if self._key_pressed(self.key_timeout):
                            key2 = sys.stdin.read(2)
                            arrow = key + key2
                            if arrow == '\x1b[A':
                                msg.linear.x = self.speed
                            elif arrow == '\x1b[B':
                                msg.linear.x = -self.speed
                            elif arrow == '\x1b[D':
                                msg.angular.z = self.turn_speed
                            elif arrow == '\x1b[C':
                                msg.angular.z = -self.turn_speed

                    # Game controls
                    elif key in ['m', 'M']:
                        cmd_str = String()
                        cmd_str.data = 'TOGGLE_MODE'
                        self.pub_game_control.publish(cmd_str)
                        print(' [ACTION] Mode Toggled! (Manual <--> AI)')
                    elif key in ['r', 'R']:
                        cmd_str = String()
                        cmd_str.data = 'RESET'
                        self.pub_game_control.publish(cmd_str)
                        print(' [ACTION] Game Reset!')

                    # Stop
                    elif key == ' ':
                        msg.linear.x = 0.0
                        msg.angular.z = 0.0
                    else:
                        msg.linear.x = last_linear
                        msg.angular.z = last_angular
                else:
                    # Timeout reached without keypress -> stop robot
                    msg.linear.x = 0.0
                    msg.angular.z = 0.0

                self.publisher_manual.publish(msg)
                self.publisher_direct.publish(msg)

                last_linear = msg.linear.x
                last_angular = msg.angular.z

        finally:
            termios.tcsetattr(
                sys.stdin,
                termios.TCSADRAIN,
                self.settings
            )

    def stop_robot(self):
        """Publish zero velocities to stop the robot."""
        msg = Twist()
        msg.linear.x = 0.0
        msg.angular.z = 0.0
        self.publisher_manual.publish(msg)
        self.publisher_direct.publish(msg)

    def destroy_node(self):
        """Clean up terminal settings, thread, and destroy node."""
        self.running = False
        self.stop_robot()
        termios.tcsetattr(
            sys.stdin,
            termios.TCSADRAIN,
            self.settings
        )
        super().destroy_node()


def main(args=None):
    """Entry point for the keyboard teleoperation node."""
    rclpy.init(args=args)
    node = KeyboardTeleop()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
