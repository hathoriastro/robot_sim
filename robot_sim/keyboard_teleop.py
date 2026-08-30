#!/usr/bin/env python3

import sys
import select
import termios
import tty
import threading

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist


class KeyboardTeleop(Node):

    def __init__(self):
        super().__init__('keyboard_teleop')

        self.publisher = self.create_publisher(
            Twist,
            '/cmd_vel',
            10
        )

        self.speed = 0.5
        self.turn_speed = 1.0

        # Berapa lama menunggu input sebelum dianggap "tidak ada tombol
        # ditekan" dan robot dihentikan. Kecil supaya responsif.
        self.key_timeout = 0.1  # detik

        self.running = True

        # Save terminal settings
        self.settings = termios.tcgetattr(sys.stdin)

        self.get_logger().info('Keyboard Teleop Started')
        self.get_logger().info('--------------------------------')
        self.get_logger().info('W / UP    : Forward')
        self.get_logger().info('S / DOWN  : Backward')
        self.get_logger().info('A / LEFT  : Turn Left')
        self.get_logger().info('D / RIGHT : Turn Right')
        self.get_logger().info('SPACE     : Stop')
        self.get_logger().info('CTRL+C    : Exit')
        self.get_logger().info('Robot akan berhenti otomatis jika tidak ada tombol ditekan')
        self.get_logger().info('--------------------------------')

        # Start keyboard thread
        self.keyboard_thread = threading.Thread(
            target=self.keyboard_loop,
            daemon=True
        )

        self.keyboard_thread.start()

    def _key_pressed(self, timeout):
        """Cek apakah ada karakter di stdin dalam batas waktu `timeout`.
        Non-blocking: kalau tidak ada input, langsung return False."""
        ready, _, _ = select.select([sys.stdin], [], [], timeout)
        return bool(ready)

    def keyboard_loop(self):

        tty.setcbreak(sys.stdin.fileno())

        try:

            last_linear = 0.0
            last_angular = 0.0

            while self.running:

                msg = Twist()

                if self._key_pressed(self.key_timeout):

                    key = sys.stdin.read(1)

                    # =========================
                    # WASD
                    # =========================

                    if key == 'w':
                        msg.linear.x = self.speed

                    elif key == 's':
                        msg.linear.x = -self.speed

                    elif key == 'a':
                        msg.angular.z = self.turn_speed

                    elif key == 'd':
                        msg.angular.z = -self.turn_speed

                    # =========================
                    # ARROW KEYS
                    # =========================

                    elif key == '\x1b':

                        # Escape sequence panah juga butuh dicek non-blocking,
                        # jaga-jaga kalau cuma tombol ESC yang ditekan.
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

                    # =========================
                    # STOP
                    # =========================

                    elif key == ' ':
                        msg.linear.x = 0.0
                        msg.angular.z = 0.0

                    else:
                        # Tombol lain diabaikan, tapi tetap publish state
                        # terakhir supaya tidak ada jeda aneh.
                        msg.linear.x = last_linear
                        msg.angular.z = last_angular

                else:
                    # Tidak ada tombol ditekan dalam key_timeout detik
                    # -> robot berhenti.
                    msg.linear.x = 0.0
                    msg.angular.z = 0.0

                self.publisher.publish(msg)

                if msg.linear.x != last_linear or msg.angular.z != last_angular:
                    self.get_logger().info(
                        f'Command -> linear: '
                        f'{msg.linear.x:.2f}, '
                        f'angular: '
                        f'{msg.angular.z:.2f}'
                    )

                last_linear = msg.linear.x
                last_angular = msg.angular.z

        finally:

            termios.tcsetattr(
                sys.stdin,
                termios.TCSADRAIN,
                self.settings
            )

    def stop_robot(self):

        msg = Twist()

        msg.linear.x = 0.0
        msg.angular.z = 0.0

        self.publisher.publish(msg)

    def destroy_node(self):

        self.running = False

        self.stop_robot()

        termios.tcsetattr(
            sys.stdin,
            termios.TCSADRAIN,
            self.settings
        )

        super().destroy_node()


def main(args=None):

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
