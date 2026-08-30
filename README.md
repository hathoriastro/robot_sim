# Robot Sim - ROS 2 Gazebo Simulation & Teleop

Paket ROS 2 ini berisi simulasi lingkungan Gazebo dengan model robot kustom (`robot.sdf`) dan kontrol pergerakan menggunakan keyboard (`keyboard_teleop`).

---

## 📁 Struktur Paket

```text
robot_sim/
├── launch/
│   └── simulation.launch.py   # Launch file untuk Gazebo & spawn robot
├── models/
│   └── robot.sdf              # Model robot (SDF)
├── worlds/
│   └── empty.sdf              # Lingkungan/world simulasi Gazebo
├── robot_sim/
│   ├── __init__.py
│   └── keyboard_teleop.py     # Node ROS 2 kontrol keyboard (cmd_vel)
├── resource/
├── test/
├── package.xml
├── setup.cfg
└── setup.py
```

---

## 🛠️ Prasyarat (Prerequisites)

Pastikan sistem Anda telah terpasang:
- **ROS 2** (Humble / Iron / Jazzy)
- **Gazebo Sim / Ignition Gazebo** (`ros_gz_sim`, `ros_gz_bridge`)
- Python 3 & `colcon`

Untuk menginstal dependensi ROS–Gazebo bridge (sesuaikan dengan distro ROS 2 Anda, misal `jazzy` atau `humble`):
```bash
sudo apt update
sudo apt install ros-${ROS_DISTRO}-ros-gz
```

---

## 🚀 Instalasi & Build

1. Buat atau masuk ke direktori workspace ROS 2 Anda:
   ```bash
   mkdir -p ~/ros2_ws/src
   cd ~/ros2_ws/src
   ```

2. Letakkan folder `robot_sim` di dalam folder `src/`.

3. Build workspace menggunakan `colcon`:
   ```bash
   cd ~/ros2_ws
   colcon build --packages-select robot_sim
   ```

4. Source overlay workspace:
   ```bash
   source ~/ros2_ws/install/setup.bash
   ```

---

## 🎮 Cara Menjalankan Simulasi

### 1. Jalankan Simulasi Gazebo (Launch)
Buka terminal baru, lakukan source environment, lalu jalankan file launch:
```bash
source ~/ros2_ws/install/setup.bash
ros2 launch robot_sim simulation.launch.py
```
*Perintah ini akan membuka Gazebo dengan world `empty.sdf` serta memuat model `robot.sdf`.*

---

### 2. Jalankan Kontrol Keyboard Teleop
Buka terminal terpisah untuk mengontrol robot:
```bash
source ~/ros2_ws/install/setup.bash
ros2 run robot_sim keyboard_teleop
```

#### ⌨️ Kontrol Tombol:
| Tombol | Aksi / Arah |
| :--- | :--- |
| `W` | Bergerak Maju |
| `S` | Bergerak Mundur |
| `A` | Belok Kiri |
| `D` | Belok Kanan |
| `Space` / `K` | Berhenti (Stop) |
| `Ctrl + C` | Keluar dari Teleop |

---

## 🔍 Debugging & Topik ROS 2

Untuk memverifikasi topik pergerakan velocity (`cmd_vel`):
```bash
ros2 topic echo /cmd_vel
```

Untuk melihat daftar topik yang aktif:
```bash
ros2 topic list
```
