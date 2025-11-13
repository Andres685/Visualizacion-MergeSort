# merge_tree_controller.py
import sys
import random
from functools import lru_cache
from collections import deque

from PySide6 import QtCore, QtWidgets, QtUiTools
from PySide6.QtWidgets import QTreeWidgetItem, QLabel, QWidget
from PySide6.QtGui import QColor, QBrush

try:
    import psutil
    import matplotlib
    matplotlib.use("QtAgg")
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    _HAS_MONITOR = True
except Exception:
    _HAS_MONITOR = False
    # el código seguirá funcionando sin monitor; solo no mostrará gráficas

# ---------------- Instrumented merge sort (generador de eventos) ----------------
def merge_sort_gen(arr, l, r):
    """Generador que ordena arr[l:r] y emite eventos:
       ('enter', l, r, snapshot)
       ('compare', i, j)
       ('take', idx)
       ('write', l, r, pos, val)
       ('exit', l, r, snapshot_final)
    """
    yield ('enter', l, r, arr[l:r])
    if r - l <= 1:
        yield ('exit', l, r, arr[l:r])
        return
    m = (l + r) // 2
    yield from merge_sort_gen(arr, l, m)
    yield from merge_sort_gen(arr, m, r)
    i, j = l, m
    temp = []
    while i < m and j < r:
        yield ('compare', i, j)
        if arr[i] <= arr[j]:
            temp.append(arr[i]); yield ('take', i); i += 1
        else:
            temp.append(arr[j]); yield ('take', j); j += 1
    while i < m:
        temp.append(arr[i]); yield ('take', i); i += 1
    while j < r:
        temp.append(arr[j]); yield ('take', j); j += 1
    for idx, val in enumerate(temp):
        pos = l + idx
        yield ('write', l, r, pos, val)
        arr[pos] = val
    yield ('exit', l, r, arr[l:r])

def make_sort_events(original):
    arr = original[:]  # copia que se muta dentro del generator
    return merge_sort_gen(arr, 0, len(arr)), arr

# ---------------- Cálculo exacto de mejor/peor caso por recurrencia ----------------
@lru_cache(maxsize=None)
def worst_case_comparisons(n):
    if n <= 1:
        return 0
    a = n // 2
    b = n - a
    return worst_case_comparisons(a) + worst_case_comparisons(b) + (n - 1)

@lru_cache(maxsize=None)
def best_case_comparisons(n):
    if n <= 1:
        return 0
    a = n // 2
    b = n - a
    return best_case_comparisons(a) + best_case_comparisons(b) + min(a, b)

# ---------------- Controller que carga el .ui y conecta todo ----------------
class MergeTreeController:
    def __init__(self, ui_filename="tree.ui"):
        # Cargar UI desde Designer
        f = QtCore.QFile(ui_filename)
        if not f.exists():
            raise FileNotFoundError(f"No se encontró '{ui_filename}' en el directorio actual.")
        f.open(QtCore.QFile.ReadOnly)
        loader = QtUiTools.QUiLoader()
        self.win = loader.load(f)
        f.close()

        # Tamaño de ventana
        self.win.setFixedSize(800, 2000)
        self.win.setWindowTitle("MergeSort - Tree Visual (controller)")

        # Buscar widgets por objectName (los definidos en Designer)
        self.tree = self.win.findChild(QtWidgets.QTreeWidget, "treeWidget")
        # proteger por si tree no existe
        if self.tree is not None:
            header = self.tree.header()
            try:
                header.setFixedHeight(70)
            except Exception:
                pass
            try:
                # setDefaultSectionSize solo afecta columnas no dimensionadas; se usa más abajo
                header.setDefaultSectionSize(200)
            except Exception:
                pass

        self.spinN = self.win.findChild(QtWidgets.QSpinBox, "spinN")
        self.btnGenerate = self.win.findChild(QtWidgets.QPushButton, "btnGenerate")
        self.btnStart = self.win.findChild(QtWidgets.QPushButton, "btnStart")
        self.btnPause = self.win.findChild(QtWidgets.QPushButton, "btnPause")
        self.btnStep = self.win.findChild(QtWidgets.QPushButton, "btnStep")
        self.btnReset = self.win.findChild(QtWidgets.QPushButton, "btnReset")
        self.spinSpeed = self.win.findChild(QtWidgets.QSpinBox, "spinSpeed")
        self.lblComparisons = self.win.findChild(QtWidgets.QLabel, "lblComparisons")
        # opcionales: etiquetas para mejor/peor caso si el diseñador las agregó
        self.lblBest = self.win.findChild(QtWidgets.QLabel, "lblBest")
        self.lblWorst = self.win.findChild(QtWidgets.QLabel, "lblWorst")
        # widget donde insertaremos el gráfico (debe existir en el .ui con ese objectName)
        self.plot_container = self.win.findChild(QtWidgets.QWidget, "plotWidget")

        # Estado / datos
        self.arr = []
        self.tree_items = {}  # mapa (l,r) -> QTreeWidgetItem
        self.generator = None
        self.sorted_copy = None
        self.timer = QtCore.QTimer(self.win)
        self.timer.timeout.connect(self.process_next_event)
        self.is_running = False
        self.comparisons = 0

        # Monitor (si psutil/matplotlib disponibles)
        self._monitor_timer = None
        self._proc = None
        self._cpu = deque()
        self._mem = deque()
        self._times = deque()
        if _HAS_MONITOR:
            try:
                self._setup_monitor(sample_interval_ms=200, window_seconds=30)
            except Exception:
                # si algo falla, desactivar monitor silenciosamente
                self._monitor_timer = None

        # Conexiones a botones
        if self.btnGenerate: self.btnGenerate.clicked.connect(self.generate)
        if self.btnStart: self.btnStart.clicked.connect(self.start)
        if self.btnPause: self.btnPause.clicked.connect(self.pause_or_resume)
        if self.btnStep: self.btnStep.clicked.connect(self.step_once)
        if self.btnReset: self.btnReset.clicked.connect(self.reset_view)
        if self.spinSpeed: self.spinSpeed.valueChanged.connect(self.on_speed_change)

        # Ajustes por defecto
        if self.spinN:
            self.spinN.setRange(1, 600)
            self.spinN.setValue(8)
        # velocidad por defecto 120 ms
        if self.spinSpeed:
            self.spinSpeed.setRange(1, 2000)
            self.spinSpeed.setValue(120)
            self.timer.setInterval(120)
        else:
            self.timer.setInterval(120)

        # Generación inicial
        self.generate()

    # ------------ Monitor: setup + sampling --------------------------------
    def _setup_monitor(self, sample_interval_ms=200, window_seconds=20):
        """Configura el monitor si psutil y matplotlib están disponibles."""
        if not _HAS_MONITOR:
            return
        self._proc = psutil.Process()
        self._sample_interval_ms = sample_interval_ms
        self._window_seconds = window_seconds
        max_points = max(10, int(window_seconds * 1000 // sample_interval_ms))
        self._cpu = deque(maxlen=max_points)
        self._mem = deque(maxlen=max_points)
        self._times = deque(maxlen=max_points)

        # preparar figura
        fig = Figure(figsize=(4,2.2), tight_layout=True)
        self._ax_cpu = fig.add_subplot(211)
        self._ax_mem = fig.add_subplot(212, sharex=self._ax_cpu)
        self._ax_cpu.set_ylabel("CPU %")
        self._ax_mem.set_ylabel("RSS (MB)")
        self._ax_mem.set_xlabel("muestras")

        self._line_cpu, = self._ax_cpu.plot([], [], lw=1.4, label="CPU%")
        self._line_mem, = self._ax_mem.plot([], [], lw=1.2, color="#66ffcc", label="RSS MB")
        self._ax_cpu.grid(True, alpha=0.25)
        self._ax_mem.grid(True, alpha=0.25)

        self._canvas = FigureCanvas(fig)
        # insertar canvas en plot_container (creado en Designer)
        if self.plot_container is not None:
            if self.plot_container.layout() is None:
                self.plot_container.setLayout(QtWidgets.QVBoxLayout())
            # limpiar lo que hubiera antes
            for i in reversed(range(self.plot_container.layout().count())):
                w = self.plot_container.layout().itemAt(i).widget()
                if w:
                    w.setParent(None)
            self.plot_container.layout().addWidget(self._canvas)

        # timer de muestreo
        self._monitor_timer = QtCore.QTimer(self.win)
        self._monitor_timer.setInterval(sample_interval_ms)
        self._monitor_timer.timeout.connect(self._sample_metrics)

        # inicializar cpu_percent para primera medición
        try:
            self._proc.cpu_percent(interval=None)
        except Exception:
            pass

    def _sample_metrics(self):
        """Muestra cpu% y rss del proceso actual y actualiza las curvas."""
        if not _HAS_MONITOR or self._proc is None:
            return
        try:
            cpu_pct = self._proc.cpu_percent(interval=None)
            mem_rss = self._proc.memory_info().rss / (1024 * 1024.0)  # MB
        except Exception:
            return

        self._cpu.append(cpu_pct)
        self._mem.append(mem_rss)
        self._times.append(len(self._times) + 1)

        # actualizar líneas
        self._line_cpu.set_data(range(len(self._cpu)), list(self._cpu))
        self._line_mem.set_data(range(len(self._mem)), list(self._mem))

        # re-escalar y dibujar
        try:
            self._ax_cpu.relim(); self._ax_cpu.autoscale_view()
            self._ax_mem.relim(); self._ax_mem.autoscale_view()
            self._canvas.draw_idle()
        except Exception:
            pass

    # ---------------- Tree building (solo con QTreeWidget que definiste en Designer) ----------------
    def build_tree(self):
        """Construye nodos en el treeWidget siguiendo la recursión de merge sort (sin ejecutar)."""
        if self.tree is None:
            return
        self.tree.clear()
        self.tree_items.clear()
        n = len(self.arr)
        def rec(l, r, parent_item):
            label = f"[{l}:{r}]"
            content = str(self.arr[l:r])
            item = QTreeWidgetItem([label, content])
            if parent_item is None:
                self.tree.addTopLevelItem(item)
            else:
                parent_item.addChild(item)
            self.tree_items[(l,r)] = item
            if r - l <= 1:
                return
            m = (l + r) // 2
            rec(l, m, item)
            rec(m, r, item)
        rec(0, n, None)
        self.tree.expandAll()
        # Ajuste de columnas: si quieres, puedes setear tamaños por defecto aquí
        try:
            header = self.tree.header()
            header.setDefaultSectionSize(200)
        except Exception:
            pass

    # ---------------- UI actions ----------------
    def generate(self):
        n = self.spinN.value() if self.spinN else 8
        self.arr = [random.randint(0, n*5) for _ in range(n)]
        self.generator = None
        self.sorted_copy = None
        self.reset_counters()
        self.build_tree()
        # actualizar cálculo best/worst
        try:
            best = best_case_comparisons(n)
            worst = worst_case_comparisons(n)
            if self.lblBest: self.lblBest.setText(f"Mejor Caso ({n}): {best}")
            if self.lblWorst: self.lblWorst.setText(f"Peor Caso ({n}): {worst}")
        except Exception:
            pass

    def reset_counters(self):
        self.comparisons = 0
        self.update_stats()

    def update_stats(self):
        if self.lblComparisons: self.lblComparisons.setText(f"Comparaciones: {self.comparisons}")

    def on_speed_change(self, v):
        try:
            self.timer.setInterval(int(v))
        except Exception:
            pass

    def start(self):
        if self.generator is None:
            self.generator, self.sorted_copy = make_sort_events(self.arr[:])
            self.reset_counters()
        if not self.is_running:
            self.is_running = True
            # iniciar monitor si existe
            try:
                if _HAS_MONITOR and self._monitor_timer is not None:
                    # limpiar series anteriores
                    self._cpu.clear(); self._mem.clear(); self._times.clear()
                    self._monitor_timer.start()
            except Exception:
                pass
            # intervalo ya fijado en spinSpeed (o por defecto 120)
            self.timer.start()

    def pause_or_resume(self):
        if self.is_running:
            # pausar ambos timers
            self.timer.stop()
            try:
                if _HAS_MONITOR and self._monitor_timer is not None:
                    self._monitor_timer.stop()
            except Exception:
                pass
            self.is_running = False
            if self.btnPause: self.btnPause.setText("Resume")
        else:
            if self.generator is None:
                self.generator, self.sorted_copy = make_sort_events(self.arr[:])
                self.reset_counters()
            try:
                if _HAS_MONITOR and self._monitor_timer is not None:
                    self._monitor_timer.start()
            except Exception:
                pass
            self.is_running = True
            self.timer.start()
            if self.btnPause: self.btnPause.setText("Pause")

    def step_once(self):
        if self.generator is None:
            self.generator, self.sorted_copy = make_sort_events(self.arr[:])
            self.reset_counters()
        try:
            ev = next(self.generator)
            self.handle_event(ev)
            self.update_stats()
        except StopIteration:
            self.generator = None
            self.is_running = False
            # al terminar, detener monitor si estaba en marcha
            try:
                if _HAS_MONITOR and self._monitor_timer is not None:
                    self._monitor_timer.stop()
            except Exception:
                pass

    def reset_view(self):
        self.timer.stop()
        self.is_running = False
        self.generator = None
        self.sorted_copy = None
        # rebuild tree from original arr (no mutación)
        self.build_tree()
        self.reset_counters()
        if self.btnPause: self.btnPause.setText("Pause")
        # detener monitor si existe
        try:
            if _HAS_MONITOR and self._monitor_timer is not None:
                self._monitor_timer.stop()
        except Exception:
            pass

    # ---------------- Event processing ----------------
    def process_next_event(self):
        if self.generator is None:
            self.timer.stop()
            self.is_running = False
            return
        try:
            ev = next(self.generator)
            self.handle_event(ev)
            self.update_stats()
        except StopIteration:
            self.timer.stop()
            self.is_running = False
            self.generator = None
            self.update_stats()
            # cuando termina, detener monitor y mostrar resumen
            try:
                if _HAS_MONITOR and self._monitor_timer is not None:
                    self._monitor_timer.stop()
            except Exception:
                pass
            self._print_monitor_summary()

    def handle_event(self, ev):
        typ = ev[0]
        if typ == 'enter':
            _, l, r, snap = ev
            item = self.tree_items.get((l,r))
            if item:
                item.setBackground(0, QBrush(QColor("#00aaff")))
                item.setText(1, str(snap))
        elif typ == 'compare':
            _, i, j = ev
            self.comparisons += 1
            # marcar hojas que contienen i y j (si existen)
            leaf_i = self.tree_items.get((i, i+1))
            leaf_j = self.tree_items.get((j, j+1))
            if leaf_i: leaf_i.setBackground(0, QBrush(QColor("#f60000")))
            if leaf_j: leaf_j.setBackground(0, QBrush(QColor("#f60000")))
        elif typ == 'take':
            pass
        elif typ == 'write':
            _, l, r, pos, val = ev
            seg_item = self.tree_items.get((l, r))
            if seg_item:
                seg_item.setText(1, f"... writing {pos}:{val} ...")
            leaf = self.tree_items.get((pos, pos+1))
            if leaf:
                leaf.setText(1, str([val]))
        elif typ == 'exit':
            _, l, r, snap = ev
            item = self.tree_items.get((l,r))
            if item:
                item.setBackground(0, QBrush(QColor("#1a8a1a")))
                item.setText(1, str(snap))

    # ---------------- Monitor summary / helper ----------------
    def _print_monitor_summary(self):
        if not _HAS_MONITOR:
            return
        try:
            max_cpu = max(self._cpu) if self._cpu else 0.0
            max_mem = max(self._mem) if self._mem else 0.0
            avg_cpu = (sum(self._cpu)/len(self._cpu)) if self._cpu else 0.0
            avg_mem = (sum(self._mem)/len(self._mem)) if self._mem else 0.0
            print(f"[Monitor] Peak CPU: {max_cpu:.1f}%  Avg CPU: {avg_cpu:.1f}%")
            print(f"[Monitor] Peak RSS: {max_mem:.2f} MB  Avg RSS: {avg_mem:.2f} MB")
        except Exception:
            pass

    # ---------------- Exponer ventana para mostrar ----------------
    def show(self):
        self.win.show()


# ----------------- Main -----------------
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    controller = MergeTreeController("tree.ui")
    controller.show()
    sys.exit(app.exec())
