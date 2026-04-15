import sys
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QLabel,
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QSlider,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPathItem,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen, QFont, QPainterPath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from simulation import Simulation


class PopGraphWidget(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(280, 70)
        self.setBackgroundBrush(QBrush(QColor(10, 22, 40)))
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.fish_history = []
        self.pred_history = []
        self.maxlen = 280
        self.sample_counter = 0
        self.sample_rate = 8

    def update(self, fish_count: int, pred_count: int):
        self.sample_counter += 1
        if self.sample_counter >= self.sample_rate:
            self.sample_counter = 0
            self.fish_history.append(fish_count)
            self.pred_history.append(pred_count)

            if len(self.fish_history) > self.maxlen:
                self.fish_history.pop(0)
                self.pred_history.pop(0)

        self.scene.clear()

        if len(self.fish_history) < 2:
            return

        max_fish = max(max(self.fish_history), 100)

        fish_path = QPainterPath()
        pred_path = QPainterPath()

        for i, (fc, pc) in enumerate(zip(self.fish_history, self.pred_history)):
            x = i
            fy = 70 - (fc / max_fish) * 65
            py = 70 - (pc / max_fish) * 65

            if i == 0:
                fish_path.moveTo(x, fy)
                pred_path.moveTo(x, py)
            else:
                fish_path.lineTo(x, fy)
                pred_path.lineTo(x, py)

        fish_item = QGraphicsPathItem(fish_path)
        fish_item.setPen(QPen(QColor(80, 180, 220), 1))
        self.scene.addItem(fish_item)

        pred_item = QGraphicsPathItem(pred_path)
        pred_item.setPen(QPen(QColor(220, 80, 80), 1))
        self.scene.addItem(pred_item)


class ControlWindow(QMainWindow):
    def __init__(self, sim: "Simulation"):
        super().__init__()
        self.sim = sim

        self.setWindowTitle("Boids — Controls")
        self.setFixedSize(340, 700)
        self.setStyleSheet("background-color: #0a1628;")

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        self._create_stats_row(layout)
        self._create_help_section(layout)
        self._create_graph_section(layout)
        self._create_sliders_section(layout)

        self.fps_label = QLabel("FPS: 0")
        self.fps_label.setStyleSheet(
            "color: #506070; font-family: monospace; font-size: 9px;"
        )
        layout.addWidget(self.fps_label)

        self.frame_count = 0
        self.fps_timer = 0

    def _create_stats_row(self, layout):
        row = QFrame()
        row.setStyleSheet("background-color: #0a1628;")
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 8, 0, 8)

        self.fish_count_label = QLabel("Fish: 0")
        self.fish_count_label.setStyleSheet(
            "color: #50b4dc; font-family: monospace; font-size: 14px; font-weight: bold;"
        )

        self.pred_count_label = QLabel("Predators: 0")
        self.pred_count_label.setStyleSheet(
            "color: #dc5050; font-family: monospace; font-size: 14px; font-weight: bold;"
        )

        h.addWidget(self.fish_count_label)
        h.addStretch()
        h.addWidget(self.pred_count_label)

        layout.addWidget(row)

    def _create_help_section(self, layout):
        frame = QFrame()
        frame.setStyleSheet("background-color: #0f1f35; border: 1px solid #2a3550;")
        v = QVBoxLayout(frame)
        v.setContentsMargins(10, 5, 10, 5)

        title = QLabel("Keyboard Shortcuts")
        title.setStyleSheet("color: #b0c0d0; font-family: monospace; font-size: 10px;")
        v.addWidget(title)

        shortcuts = [
            ("UP / DOWN", "Add/Remove fish"),
            ("P", "Add predator"),
            ("[ / ]", "Predator speed"),
            ("C", "Toggle patrol"),
            ("ESC", "Quit"),
        ]

        for key, action in shortcuts:
            row = QFrame()
            row.setStyleSheet("background-color: #0f1f35;")
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 0, 0, 0)

            k = QLabel(key)
            k.setStyleSheet(
                "color: #70a0c0; font-family: monospace; font-size: 10px; font-weight: bold;"
            )
            k.setFixedWidth(60)

            a = QLabel(action)
            a.setStyleSheet("color: #8090a0; font-family: monospace; font-size: 10px;")

            h.addWidget(k)
            h.addWidget(a)

            v.addWidget(row)

        layout.addWidget(frame)

    def _create_graph_section(self, layout):
        frame = QFrame()
        frame.setStyleSheet("background-color: #0a1628; border: 1px solid #2a3550;")
        v = QVBoxLayout(frame)
        v.setContentsMargins(10, 5, 10, 5)

        title = QLabel("Population")
        title.setStyleSheet("color: #b0c0d0; font-family: monospace; font-size: 10px;")
        v.addWidget(title)

        self.graph = PopGraphWidget()
        v.addWidget(self.graph)

        legend = QFrame()
        legend.setStyleSheet("background-color: #0a1628;")
        h = QHBoxLayout(legend)
        h.setContentsMargins(0, 5, 0, 0)

        fish_lbl = QLabel("● Fish")
        fish_lbl.setStyleSheet(
            "color: #50b4dc; font-family: monospace; font-size: 9px;"
        )
        pred_lbl = QLabel("● Predators")
        pred_lbl.setStyleSheet(
            "color: #dc5050; font-family: monospace; font-size: 9px;"
        )

        h.addWidget(fish_lbl)
        h.addStretch()
        h.addWidget(pred_lbl)

        v.addWidget(legend)

        layout.addWidget(frame)

    def _create_sliders_section(self, layout):
        from constants import (
            VISUAL_RANGE,
            SEPARATION_RANGE,
            FLEE_RANGE,
            FLEE_WEIGHT,
            REPRODUCE_CHANCE,
            PRED_SPEED,
        )

        frame = QFrame()
        frame.setStyleSheet("background-color: #0a1628; border: 1px solid #2a3550;")
        v = QVBoxLayout(frame)
        v.setContentsMargins(10, 5, 10, 5)

        title = QLabel("Parameters")
        title.setStyleSheet("color: #b0c0d0; font-family: monospace; font-size: 10px;")
        v.addWidget(title)

        self.slider_configs = [
            ("Predator Speed", 0.5, 5.0, 0.1, PRED_SPEED, "speed"),
            ("Visual Range", 30, 150, 5, VISUAL_RANGE, "visual_range"),
            ("Separation", 10, 50, 1, SEPARATION_RANGE, "separation"),
            ("Flee Range", 50, 200, 5, FLEE_RANGE, "flee_range"),
            ("Flee Weight", 1.0, 10.0, 0.1, FLEE_WEIGHT, "flee_weight"),
            ("Reproduce", 0.0, 0.01, 0.0005, REPRODUCE_CHANCE, "reproduce"),
        ]

        self.sliders = {}

        for label, min_val, max_val, step, default, key in self.slider_configs:
            row = QFrame()
            row.setStyleSheet("background-color: #0f1f35; border-radius: 4px;")
            row.setMinimumHeight(50)
            h_row = QHBoxLayout(row)
            h_row.setContentsMargins(10, 5, 10, 5)

            label_text = QLabel(f"{label}: {default:.1f}")
            label_text.setFixedWidth(130)
            label_text.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            label_text.setStyleSheet("""
                color: #90a0b0;
                font-family: monospace;
                font-size: 14px;
                background-color: transparent;
            """)
            h_row.addWidget(label_text)

            slider = QSlider(Qt.Horizontal)
            slider.setMinimum(int(min_val / step))
            slider.setMaximum(int(max_val / step))
            slider.setValue(int(default / step))
            slider.valueChanged.connect(
                lambda v, s=step, l=label_text, k=key: self._on_slider(s, l, k, v)
            )
            h_row.addWidget(slider)

            self.sliders[key] = (slider, label_text, step)

            v.addWidget(row)

        layout.addWidget(frame)

    def _on_slider(self, step: float, label: QLabel, key: str, value: int):
        val = value * step

        import constants

        if key == "speed":
            for pred in self.sim.predators:
                pred.speed = val
            label.setText(f"Predator Speed: {val:.1f}")
        elif key == "visual_range":
            constants.VISUAL_RANGE = val
            label.setText(f"Visual Range: {int(val)}")
        elif key == "separation":
            constants.SEPARATION_RANGE = val
            label.setText(f"Separation: {int(val)}")
        elif key == "flee_range":
            constants.FLEE_RANGE = val
            label.setText(f"Flee Range: {int(val)}")
        elif key == "flee_weight":
            constants.FLEE_WEIGHT = val
            label.setText(f"Flee Weight: {val:.1f}")
        elif key == "reproduce":
            constants.REPRODUCE_CHANCE = val
            label.setText(f"Reproduce: {val:.4f}")

    def sync(self, fps: float = 60.0):
        self.fish_count_label.setText(f"Fish: {len(self.sim.fish)}")
        self.pred_count_label.setText(f"Predators: {len(self.sim.predators)}")
        self.graph.update(len(self.sim.fish), len(self.sim.predators))
        self.fps_label.setText(f"FPS: {fps:.0f}")

    def is_alive(self) -> bool:
        return QApplication.instance() is not None
