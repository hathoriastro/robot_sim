"""Time Attack Waypoint Chaser Master Node for ROS 2 simulation."""

import math
import random
import time
from collections import deque

from geometry_msgs.msg import Point, Twist

from nav_msgs.msg import Odometry

import rclpy
from rclpy.node import Node

from std_msgs.msg import ColorRGBA, String

from visualization_msgs.msg import Marker, MarkerArray


def quaternion_to_yaw(x: float, y: float, z: float, w: float) -> float:
    """Convert a quaternion orientation into yaw angle in radians."""
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    return math.atan2(siny_cosp, cosy_cosp)


def normalize_angle(angle: float) -> float:
    """Normalize an angle to the range [-pi, pi]."""
    while angle > math.pi:
        angle -= 2.0 * math.pi
    while angle < -math.pi:
        angle += 2.0 * math.pi
    return angle


class TimeAttackMasterNode(Node):
    """Game master node managing state, scoring, autopilot, and 3D HUD."""

    def __init__(self):
        """Initialize parameters, subscribers, publishers, and timer."""
        super().__init__('time_attack_master_node')

        # Parameters
        self.arena_size = 7.0  # 7m x 7m playable area (-3.5 to 3.5)
        self.initial_time = 60.0  # 60 seconds
        self.bonus_time = 5.0  # +5s per coin
        self.target_radius = 0.45  # Distance threshold to capture coin
        self.combo_timeout = 4.0  # Seconds for combo multiplier

        # Game State
        self.mode = 'MANUAL'  # 'MANUAL' or 'AUTOPILOT'
        self.game_state = 'PLAYING'  # 'PLAYING' or 'GAME_OVER'
        self.time_remaining = self.initial_time
        self.score = 0
        self.coins_collected = 0
        self.combo_count = 0
        self.last_capture_time = 0.0
        self.high_score = 0
        self.status_message = 'WELCOME TO COIN RUSH!'
        self.status_message_expire = time.time() + 4.0

        # Robot Pose from /odom
        self.robot_x = 0.0
        self.robot_y = 0.0
        self.robot_yaw = 0.0
        self.odom_received = False

        # Target Waypoint (Coin)
        self.target_x = 2.0
        self.target_y = 1.5
        self.coin_spin_angle = 0.0

        # Breadcrumb Trail
        self.trail_points = deque(maxlen=300)
        self.last_trail_time = time.time()

        # Cleared effect marker
        self.cleared_effect_pos = None
        self.cleared_effect_timer = 0.0

        # Manual input from teleop
        self.manual_cmd = Twist()

        # Autopilot PID parameters
        self.kp_linear = 0.8
        self.max_linear_speed = 1.2
        self.min_linear_speed = 0.2
        self.kp_angular = 2.2
        self.max_angular_speed = 2.0

        # ROS 2 Subscribers & Publishers
        self.sub_odom = self.create_subscription(
            Odometry,
            '/odom',
            self.odom_callback,
            10
        )

        self.sub_manual_cmd = self.create_subscription(
            Twist,
            '/cmd_vel_manual',
            self.manual_cmd_callback,
            10
        )

        self.sub_game_control = self.create_subscription(
            String,
            '/game_control',
            self.game_control_callback,
            10
        )

        self.pub_cmd_vel = self.create_publisher(
            Twist,
            '/cmd_vel',
            10
        )

        self.pub_markers = self.create_publisher(
            MarkerArray,
            '/visualization_marker_array',
            10
        )

        # Timers
        self.dt = 0.05  # 20 Hz loop
        self.last_tick_time = time.time()
        self.timer = self.create_timer(self.dt, self.game_loop)

        self.spawn_new_target()
        self.get_logger().info('Time Attack Master Node initialized!')
        self.print_terminal_banner()

    def print_terminal_banner(self):
        """Print game status banner to standard terminal output."""
        print('\n' + '=' * 55)
        print('   🎮 TIME ATTACK: COIN RUSH (EXPO ROBOTIKA) 🎮')
        print('=' * 55)
        status_line = (
            f' Mode: {self.mode} | Waktu: {self.time_remaining:.0f}s '
            f'| Skor: {self.score}'
        )
        print(status_line)
        print(" Tekan 'W/A/S/D' untuk mengontrol robot")
        print(" Tekan 'M' untuk ganti Mode (Manual <--> Autopilot)")
        print(" Tekan 'R' untuk Instant Reset Game")
        print('=' * 55 + '\n')

    def odom_callback(self, msg: Odometry):
        """Update robot pose estimate and record path breadcrumbs."""
        self.robot_x = msg.pose.pose.position.x
        self.robot_y = msg.pose.pose.position.y
        q = msg.pose.pose.orientation
        self.robot_yaw = quaternion_to_yaw(q.x, q.y, q.z, q.w)
        self.odom_received = True

        # Update trail
        now = time.time()
        if now - self.last_trail_time > 0.15:
            point = Point(x=self.robot_x, y=self.robot_y, z=0.02)
            self.trail_points.append(point)
            self.last_trail_time = now

    def manual_cmd_callback(self, msg: Twist):
        """Receive manual velocity command from teleop node."""
        self.manual_cmd = msg

    def game_control_callback(self, msg: String):
        """Handle incoming control commands like mode toggle and reset."""
        command = msg.data.strip().upper()
        if command == 'TOGGLE_MODE':
            self.mode = 'AUTOPILOT' if self.mode == 'MANUAL' else 'MANUAL'
            self.status_message = f'MODE SWITCHED TO: {self.mode}'
            self.status_message_expire = time.time() + 2.5
            self.get_logger().info(f'[MODE SWITCH] Current mode: {self.mode}')
        elif command == 'RESET':
            self.reset_game()
        elif command == 'SET_MANUAL':
            self.mode = 'MANUAL'
        elif command == 'SET_AUTOPILOT':
            self.mode = 'AUTOPILOT'

    def reset_game(self):
        """Reset score, timer, and spawn first waypoint for a new round."""
        if self.score > self.high_score:
            self.high_score = self.score
        self.time_remaining = self.initial_time
        self.score = 0
        self.coins_collected = 0
        self.combo_count = 0
        self.game_state = 'PLAYING'
        self.trail_points.clear()
        self.spawn_new_target()
        self.status_message = '🚀 GAME RESET! GO GO GO!'
        self.status_message_expire = time.time() + 2.5
        self.get_logger().info('=== GAME HAS BEEN RESET! ===')

    def spawn_new_target(self):
        """Randomly position a new coin target within the playable arena."""
        min_dist = 1.8
        half_arena = (self.arena_size / 2.0) - 0.5

        for _ in range(50):
            cand_x = round(random.uniform(-half_arena, half_arena), 2)
            cand_y = round(random.uniform(-half_arena, half_arena), 2)
            dist_to_robot = math.hypot(
                cand_x - self.robot_x,
                cand_y - self.robot_y
            )
            if dist_to_robot >= min_dist:
                self.target_x = cand_x
                self.target_y = cand_y
                return

        # Fallback
        self.target_x = round(random.uniform(-half_arena, half_arena), 2)
        self.target_y = round(random.uniform(-half_arena, half_arena), 2)

    def game_loop(self):
        """Execute periodic game update, collision check, and publish cmds."""
        now = time.time()
        dt = now - self.last_tick_time
        self.last_tick_time = now

        # Update Countdown Timer
        if self.game_state == 'PLAYING':
            self.time_remaining -= dt
            if self.time_remaining <= 0.0:
                self.time_remaining = 0.0
                self.game_state = 'GAME_OVER'
                if self.score > self.high_score:
                    self.high_score = self.score
                self.status_message = (
                    f'🛑 GAME OVER! FINAL SCORE: {self.score}'
                )
                self.status_message_expire = time.time() + 9999.0
                self.get_logger().info(
                    f'*** GAME OVER! Final Score: {self.score}, '
                    f'Coins: {self.coins_collected} ***'
                )

        # Check Waypoint Capture
        if self.game_state == 'PLAYING' and self.odom_received:
            dist = math.hypot(
                self.target_x - self.robot_x,
                self.target_y - self.robot_y
            )
            if dist < self.target_radius:
                self.handle_target_captured()

        # Compute & Publish Control
        out_cmd = Twist()
        if self.game_state == 'PLAYING':
            if self.mode == 'MANUAL':
                out_cmd = self.manual_cmd
            else:
                out_cmd = self.compute_autopilot_cmd()
        else:
            out_cmd.linear.x = 0.0
            out_cmd.angular.z = 0.0

        self.pub_cmd_vel.publish(out_cmd)

        # Publish Visual Markers
        self.publish_visual_markers()

    def handle_target_captured(self):
        """Process score increment, combo calculation, and effects."""
        now = time.time()
        self.coins_collected += 1
        self.time_remaining += self.bonus_time

        # Combo calculation
        time_since_last = now - self.last_capture_time
        if self.last_capture_time > 0 and time_since_last < self.combo_timeout:
            self.combo_count += 1
            points = 100 * (1 + self.combo_count)
            combo_text = (
                f'🔥 COMBO x{self.combo_count + 1}! +{points} PTS '
                f'(+{int(self.bonus_time)}s)'
            )
        else:
            self.combo_count = 0
            points = 100
            combo_text = f'⭐ COIN +{points} PTS (+{int(self.bonus_time)}s)'

        self.score += points
        self.last_capture_time = now
        self.status_message = combo_text
        self.status_message_expire = now + 2.0

        # Cleared effect
        self.cleared_effect_pos = (self.target_x, self.target_y)
        self.cleared_effect_timer = now + 0.6

        # Terminal beep & log
        log_text = (
            f'\a[POINT!] {combo_text} | Total Score: {self.score} '
            f'| Time Left: {self.time_remaining:.1f}s'
        )
        print(log_text)
        self.spawn_new_target()

    def compute_autopilot_cmd(self) -> Twist:
        """Compute smooth turn-first and proportional deceleration command."""
        cmd = Twist()
        if not self.odom_received:
            return cmd

        dx = self.target_x - self.robot_x
        dy = self.target_y - self.robot_y
        dist = math.hypot(dx, dy)
        target_yaw = math.atan2(dy, dx)
        angle_err = normalize_angle(target_yaw - self.robot_yaw)

        # If angle error is large (> 35 deg), turn in place first
        if abs(angle_err) > math.radians(35):
            cmd.linear.x = 0.0
            raw_w = self.kp_angular * angle_err
            cmd.angular.z = max(
                -self.max_angular_speed,
                min(self.max_angular_speed, raw_w)
            )
        else:
            # Drive forward with proportional steering
            raw_v = self.kp_linear * dist
            # Smooth deceleration when close
            if dist < 1.0:
                raw_v = max(self.min_linear_speed, raw_v)
            cmd.linear.x = min(self.max_linear_speed, raw_v)

            raw_w = (self.kp_angular * 1.2) * angle_err
            cmd.angular.z = max(
                -self.max_angular_speed,
                min(self.max_angular_speed, raw_w)
            )

        return cmd

    def publish_visual_markers(self):
        """Publish all 3D visualization markers and HUD text into RViz2."""
        markers = MarkerArray()
        now_msg = self.get_clock().now().to_msg()
        self.coin_spin_angle += 0.08

        # 1. Arena Boundary
        boundary_marker = Marker()
        boundary_marker.header.frame_id = 'odom'
        boundary_marker.header.stamp = now_msg
        boundary_marker.ns = 'arena'
        boundary_marker.id = 0
        boundary_marker.type = Marker.LINE_STRIP
        boundary_marker.action = Marker.ADD
        boundary_marker.scale.x = 0.08  # Line width
        boundary_marker.color = ColorRGBA(r=0.2, g=0.8, b=1.0, a=0.8)
        h = self.arena_size / 2.0
        boundary_marker.points = [
            Point(x=-h, y=-h, z=0.0),
            Point(x=h, y=-h, z=0.0),
            Point(x=h, y=h, z=0.0),
            Point(x=-h, y=h, z=0.0),
            Point(x=-h, y=-h, z=0.0),
        ]
        markers.markers.append(boundary_marker)

        # 2. Waypoint Coin (Cylinder)
        coin_marker = Marker()
        coin_marker.header.frame_id = 'odom'
        coin_marker.header.stamp = now_msg
        coin_marker.ns = 'target_coin'
        coin_marker.id = 1
        coin_marker.type = Marker.CYLINDER
        coin_marker.action = Marker.ADD
        coin_marker.pose.position.x = self.target_x
        coin_marker.pose.position.y = self.target_y
        hover_z = 0.35 + 0.08 * math.sin(self.coin_spin_angle * 2.0)
        coin_marker.pose.position.z = hover_z
        coin_marker.scale.x = self.target_radius * 2.0
        coin_marker.scale.y = self.target_radius * 2.0
        coin_marker.scale.z = 0.15
        coin_marker.color = ColorRGBA(r=1.0, g=0.84, b=0.0, a=0.85)  # Gold
        markers.markers.append(coin_marker)

        # 2b. Arrow indicator above coin
        arrow_marker = Marker()
        arrow_marker.header.frame_id = 'odom'
        arrow_marker.header.stamp = now_msg
        arrow_marker.ns = 'target_arrow'
        arrow_marker.id = 2
        arrow_marker.type = Marker.ARROW
        arrow_marker.action = Marker.ADD
        arrow_marker.scale.x = 0.15  # Shaft diameter
        arrow_marker.scale.y = 0.25  # Head diameter
        arrow_marker.scale.z = 0.2   # Head length
        arrow_marker.color = ColorRGBA(r=1.0, g=0.3, b=0.1, a=0.9)
        top_z = coin_marker.pose.position.z + 0.6
        tip_z = coin_marker.pose.position.z + 0.15
        arrow_marker.points = [
            Point(x=self.target_x, y=self.target_y, z=top_z),
            Point(x=self.target_x, y=self.target_y, z=tip_z),
        ]
        markers.markers.append(arrow_marker)

        # 3. Cleared Flash Effect (if active)
        if self.cleared_effect_pos and time.time() < self.cleared_effect_timer:
            flash_marker = Marker()
            flash_marker.header.frame_id = 'odom'
            flash_marker.header.stamp = now_msg
            flash_marker.ns = 'flash_effect'
            flash_marker.id = 3
            flash_marker.type = Marker.CYLINDER
            flash_marker.action = Marker.ADD
            flash_marker.pose.position.x = self.cleared_effect_pos[0]
            flash_marker.pose.position.y = self.cleared_effect_pos[1]
            flash_marker.pose.position.z = 0.1
            flash_marker.scale.x = self.target_radius * 2.8
            flash_marker.scale.y = self.target_radius * 2.8
            flash_marker.scale.z = 0.05
            flash_marker.color = ColorRGBA(r=0.1, g=1.0, b=0.2, a=0.9)  # Green
            markers.markers.append(flash_marker)

        # 4. Robot Trail
        if len(self.trail_points) > 1:
            trail_marker = Marker()
            trail_marker.header.frame_id = 'odom'
            trail_marker.header.stamp = now_msg
            trail_marker.ns = 'trail'
            trail_marker.id = 4
            trail_marker.type = Marker.LINE_STRIP
            trail_marker.action = Marker.ADD
            trail_marker.scale.x = 0.05  # Trail thickness
            trail_marker.color = ColorRGBA(r=1.0, g=0.4, b=0.8, a=0.7)  # Pink
            trail_marker.points = list(self.trail_points)
            markers.markers.append(trail_marker)

        # 5. Floating 3D HUD: Main Status / Score Board
        hud_main = Marker()
        hud_main.header.frame_id = 'odom'
        hud_main.header.stamp = now_msg
        hud_main.ns = 'hud'
        hud_main.id = 5
        hud_main.type = Marker.TEXT_VIEW_FACING
        hud_main.action = Marker.ADD
        hud_main.pose.position.x = 0.0
        hud_main.pose.position.y = (self.arena_size / 2.0) + 0.6
        hud_main.pose.position.z = 2.2
        hud_main.scale.z = 0.45  # Text size

        mins = int(self.time_remaining) // 60
        secs = int(self.time_remaining) % 60
        hud_main.text = (
            f'⏱️ TIME: {mins:02d}:{secs:02d}  |  '
            f'🏆 SCORE: {self.score}  |  '
            f'🪙 COINS: {self.coins_collected}'
        )
        if self.time_remaining > 10.0:
            hud_main.color = ColorRGBA(r=1.0, g=1.0, b=1.0, a=1.0)
        else:
            # Flashing Red when time is low
            flash = math.sin(time.time() * 8.0) > 0
            alpha = 1.0 if flash else 0.4
            hud_main.color = ColorRGBA(r=1.0, g=0.2, b=0.2, a=alpha)
        markers.markers.append(hud_main)

        # 6. Floating 3D HUD: Mode & Sub-banner
        hud_sub = Marker()
        hud_sub.header.frame_id = 'odom'
        hud_sub.header.stamp = now_msg
        hud_sub.ns = 'hud'
        hud_sub.id = 6
        hud_sub.type = Marker.TEXT_VIEW_FACING
        hud_sub.action = Marker.ADD
        hud_sub.pose.position.x = 0.0
        hud_sub.pose.position.y = (self.arena_size / 2.0) + 0.6
        hud_sub.pose.position.z = 1.6
        hud_sub.scale.z = 0.35

        mode_badge = (
            '🎮 MODE: MANUAL [WASD]' if self.mode == 'MANUAL'
            else '🤖 MODE: AUTOPILOT [AI]'
        )
        hud_sub.text = f'{mode_badge}  |  [M: Switch Mode]  [R: Reset]'
        if self.mode == 'MANUAL':
            hud_sub.color = ColorRGBA(r=0.2, g=0.9, b=1.0, a=0.95)
        else:
            hud_sub.color = ColorRGBA(r=0.4, g=1.0, b=0.4, a=0.95)
        markers.markers.append(hud_sub)

        # 7. Floating Banner / Toast Message
        if time.time() < self.status_message_expire:
            hud_toast = Marker()
            hud_toast.header.frame_id = 'odom'
            hud_toast.header.stamp = now_msg
            hud_toast.ns = 'hud'
            hud_toast.id = 7
            hud_toast.type = Marker.TEXT_VIEW_FACING
            hud_toast.action = Marker.ADD
            hud_toast.pose.position.x = 0.0
            hud_toast.pose.position.y = 0.0
            hud_toast.pose.position.z = 1.2
            hud_toast.scale.z = 0.55
            hud_toast.text = self.status_message
            if 'GAME OVER' in self.status_message:
                hud_toast.color = ColorRGBA(r=1.0, g=0.1, b=0.1, a=1.0)
            elif 'COMBO' in self.status_message or (
                'COIN' in self.status_message
            ):
                hud_toast.color = ColorRGBA(r=1.0, g=0.85, b=0.0, a=1.0)
            else:
                hud_toast.color = ColorRGBA(r=0.2, g=1.0, b=0.8, a=1.0)
            markers.markers.append(hud_toast)

        self.pub_markers.publish(markers)


def main(args=None):
    """Entry point for the time attack master node."""
    rclpy.init(args=args)
    node = TimeAttackMasterNode()
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
