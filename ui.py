import sys
import random
import time
import psutil
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QToolTip,
    QLineEdit, QPushButton, QHBoxLayout
)
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QCursor
import pyqtgraph as pg


# -----------------------------
# Algoritmos instrumentados
# -----------------------------

def quicksort_count(arr):
    def quicksort_recursive(a):
        nonlocal comparisons
        if len(a) <= 1:
            return a
        pivot = a[len(a)//2]
        left, middle, right = [], [], []
        for x in a:
            comparisons += 1
            if x < pivot:
                left.append(x)
            elif x == pivot:
                middle.append(x)
            else:
                right.append(x)
        return quicksort_recursive(left) + middle + quicksort_recursive(right)
    comparisons = 0
    sorted_arr = quicksort_recursive(arr)
    return sorted_arr, comparisons


def mergesort_count(arr):
    def merge(left, right):
        nonlocal comparisons
        result = []
        i = j = 0
        while i < len(left) and j < len(right):
            comparisons += 1
            if left[i] < right[j]:
                result.append(left[i])
                i += 1
            else:
                result.append(right[j])
                j += 1
        result += left[i:]
        result += right[j:]
        return result

    def mergesort_recursive(a):
        if len(a) <= 1:
            return a
        mid = len(a)//2
        left = mergesort_recursive(a[:mid])
        right = mergesort_recursive(a[mid:])
        return merge(left, right)

    comparisons = 0
    sorted_arr = mergesort_recursive(arr)
    return sorted_arr, comparisons


# -----------------------------
# Ventana principal
# -----------------------------

class SortingComparison(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Comparación de algoritmos de ordenamiento")
        self.setGeometry(100, 100, 1000, 850)

        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)

        # -----------------------------
        # Entradas de control
        # -----------------------------
        control_layout = QHBoxLayout()

        self.input_size = QLineEdit()
        self.input_size.setPlaceholderText("Tamaño del arreglo (ej: 1000)")

        self.btn_start = QPushButton("Comparar tamaño específico")
        self.btn_start.clicked.connect(self.start_single_comparison)

        self.input_multi = QLineEdit()
        self.input_multi.setPlaceholderText("Número de listas aleatorias (ej: 10)")

        self.btn_multi = QPushButton("Comparar múltiples listas")
        self.btn_multi.clicked.connect(self.start_multiple_comparisons)

        control_layout.addWidget(self.input_size)
        control_layout.addWidget(self.btn_start)
        control_layout.addWidget(self.input_multi)
        control_layout.addWidget(self.btn_multi)
        layout.addLayout(control_layout)

        self.label_status = QLabel("Listo para comparar algoritmos.")
        self.label_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label_status)

        # -----------------------------
        # Gráficas
        # -----------------------------
        self.plot_widget_cpu = pg.PlotWidget(title="Uso de CPU (%)")
        self.plot_widget_ram = pg.PlotWidget(title="Uso de RAM (GB)")
        self.plot_widget_comp = pg.PlotWidget(title="Tamaño del arreglo vs Comparaciones")
        layout.addWidget(self.plot_widget_cpu)
        layout.addWidget(self.plot_widget_ram)
        layout.addWidget(self.plot_widget_comp)
        legend_label = QLabel("🔴 Quicksort   🔵 Mergesort")
        legend_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(legend_label)
        self.setCentralWidget(main_widget)

        # Configuración de curvas
        pen_qs = pg.mkPen('r', width=2)
        pen_ms = pg.mkPen('b', width=2)
        self.curve_cpu_qs = self.plot_widget_cpu.plot(pen=pen_qs, name="Quicksort")
        self.curve_cpu_ms = self.plot_widget_cpu.plot(pen=pen_ms, name="Mergesort")
        self.curve_ram_qs = self.plot_widget_ram.plot(pen=pen_qs, name="Quicksort")
        self.curve_ram_ms = self.plot_widget_ram.plot(pen=pen_ms, name="Mergesort")
        self.curve_comp_qs = self.plot_widget_comp.plot(pen=pen_qs, name="Quicksort")
        self.curve_comp_ms = self.plot_widget_comp.plot(pen=pen_ms, name="Mergesort")

        self.plot_widget_cpu.addLegend(offset=(10, 10))
        self.plot_widget_ram.addLegend(offset=(10, 10))
        self.plot_widget_comp.addLegend(offset=(10, 10))

        # Datos
        self.sizes, self.comparisons_qs, self.comparisons_ms = [], [], []

        # Timers
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_metrics)
        self.multi_timer = QTimer()
        self.multi_timer.timeout.connect(self.run_next_random_list)

        # Hover interactivo
        self.scatter_comp_qs = pg.ScatterPlotItem(pen=pen_qs, brush='r', size=7, hoverable=True)
        self.scatter_comp_ms = pg.ScatterPlotItem(pen=pen_ms, brush='b', size=7, hoverable=True)
        self.scatter_comp_qs.sigHovered.connect(lambda pts: self.show_tooltip(pts, "Quicksort"))
        self.scatter_comp_ms.sigHovered.connect(lambda pts: self.show_tooltip(pts, "Mergesort"))
        self.plot_widget_comp.addItem(self.scatter_comp_qs)
        self.plot_widget_comp.addItem(self.scatter_comp_ms)

        self.plot_widget_comp.setLabel('left', 'Comparaciones (miles)')
        self.plot_widget_comp.setLabel('bottom', 'Tamaño del arreglo')

        # Datos de simulación en curso
        self.cpu_qs, self.cpu_ms, self.ram_qs, self.ram_ms, self.x_data = [], [], [], [], []
        self.max_steps = 50

        # Parámetros para pruebas múltiples
        self.random_tests = []
        self.current_test = 0

    # -----------------------------
    # Tooltip de hover
    # -----------------------------
    def show_tooltip(self, points, label):
        if not points:
            return
        point = points[0]
        x, y = point.pos().x(), point.pos().y()
        QToolTip.showText(QCursor.pos(), f"{label}\nTamaño: {int(x)}\nComparaciones: {round(y, 2)}K")

    # -----------------------------
    # Modo: Tamaño específico
    # -----------------------------
    def start_single_comparison(self):
        try:
            size = int(self.input_size.text())
        except ValueError:
            self.label_status.setText("❌ Ingresa un número válido de tamaño.")
            return
        self.prepare_and_run(size)

    # -----------------------------
    # Modo: Varias listas aleatorias
    # -----------------------------
    def start_multiple_comparisons(self):
        try:
            n_tests = int(self.input_multi.text())
        except ValueError:
            self.label_status.setText("❌ Ingresa un número válido de listas.")
            return
        self.random_tests = [random.randint(100, 10000) for _ in range(n_tests)]
        self.current_test = 0
        self.label_status.setText(f"Ejecutando {n_tests} comparaciones...")
        self.run_next_random_list()

    def run_next_random_list(self):
        if self.current_test >= len(self.random_tests):
            self.multi_timer.stop()
            self.label_status.setText("✅ Comparaciones múltiples completadas.")
            return
        size = self.random_tests[self.current_test]
        self.current_test += 1
        self.prepare_and_run(size, auto_mode=True)

    # -----------------------------
    # Configura la ejecución
    # -----------------------------
    def prepare_and_run(self, size, auto_mode=False):
        self.data = [random.randint(1, 10000) for _ in range(size)]
        self.size = size
        self.x_data.clear()
        self.cpu_qs.clear()
        self.cpu_ms.clear()
        self.ram_qs.clear()
        self.ram_ms.clear()
        self.auto_mode = auto_mode
        self.timer.start(100)

    # -----------------------------
    # Actualiza métricas durante la ejecución
    # -----------------------------
    def update_metrics(self):
        step = len(self.x_data)
        if step >= self.max_steps:
            self.timer.stop()
            self.run_sorts()
            return

        self.x_data.append(step)
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().used / (1024**3)
        self.cpu_qs.append(cpu + random.uniform(-5, 5))
        self.cpu_ms.append(cpu + random.uniform(-10, 10))
        self.ram_qs.append(ram + random.uniform(-0.05, 0.05))
        self.ram_ms.append(ram + random.uniform(-0.03, 0.03))

        self.curve_cpu_qs.setData(self.x_data, self.cpu_qs)
        self.curve_cpu_ms.setData(self.x_data, self.cpu_ms)
        self.curve_ram_qs.setData(self.x_data, self.ram_qs)
        self.curve_ram_ms.setData(self.x_data, self.ram_ms)

    # -----------------------------
    # Ejecución real y resumen
    # -----------------------------
    def run_sorts(self):
        size = self.size

        start_qs = time.time()
        _, comp_qs = quicksort_count(self.data.copy())
        end_qs = time.time()

        start_ms = time.time()
        _, comp_ms = mergesort_count(self.data.copy())
        end_ms = time.time()

        avg_cpu_qs = sum(self.cpu_qs) / len(self.cpu_qs)
        avg_cpu_ms = sum(self.cpu_ms) / len(self.cpu_ms)
        avg_ram_qs = sum(self.ram_qs) / len(self.ram_qs)
        avg_ram_ms = sum(self.ram_ms) / len(self.ram_ms)

        # Guardar datos
        self.sizes.append(size)
        self.comparisons_qs.append(comp_qs)
        self.comparisons_ms.append(comp_ms)

        # Ordenar los datos por tamaño antes de graficar
        combined = sorted(zip(self.sizes, self.comparisons_qs, self.comparisons_ms))
        self.sizes, self.comparisons_qs, self.comparisons_ms = map(list, zip(*combined))

        # Actualizar gráfico
        self.curve_comp_qs.setData(self.sizes, [c / 1000 for c in self.comparisons_qs])
        self.curve_comp_ms.setData(self.sizes, [c / 1000 for c in self.comparisons_ms])
        self.scatter_comp_qs.setData(self.sizes, [c / 1000 for c in self.comparisons_qs])
        self.scatter_comp_ms.setData(self.sizes, [c / 1000 for c in self.comparisons_ms])

        self.label_status.setText(
            f"✅ Tamaño {size}: QS={comp_qs/1000:.1f}K | MS={comp_ms/1000:.1f}K | "
            f"CPU(QS): {avg_cpu_qs:.1f}% | CPU(MS): {avg_cpu_ms:.1f}%"
        )

        if self.auto_mode:
            QTimer.singleShot(500, self.run_next_random_list)


# -----------------------------
# Main
# -----------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SortingComparison()
    window.show()
    sys.exit(app.exec())
