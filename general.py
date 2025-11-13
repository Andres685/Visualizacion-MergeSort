# general.py (versión corregida para cargar y mostrar exactamente el .ui)
import sys
import subprocess
import importlib
import traceback
from types import ModuleType
from pathlib import Path

from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton, QLabel
from PySide6 import QtWidgets

def try_import(module_name: str):
    try:
        return importlib.import_module(module_name)
    except Exception:
        return None

def find_window_class(mod: ModuleType, candidates: list):
    if mod is None:
        return None
    for name in candidates:
        cls = getattr(mod, name, None)
        if isinstance(cls, type):
            return cls
    return None

def run_subprocess(script_path: str, status_label: QLabel = None):
    try:
        subprocess.Popen([sys.executable, script_path])
    except Exception as e:
        if status_label:
            status_label.setText(f"Error al ejecutar {script_path}: {e}")

def instantiate_and_show(cls):
    try:
        inst = cls()
        if isinstance(inst, QtWidgets.QWidget):
            inst.show()
            return inst
        if hasattr(inst, "win") and isinstance(inst.win, QtWidgets.QWidget):
            inst.win.show()
            return inst
        if hasattr(inst, "show") and callable(inst.show):
            inst.show()
            return inst
    except Exception:
        traceback.print_exc()
    return None

def load_ui_and_wire(ui_filename="comparaciones.ui"):
    f = QFile(ui_filename)
    if not f.exists():
        raise FileNotFoundError(f"No se encontró '{ui_filename}'")
    if not f.open(QFile.ReadOnly):
        raise RuntimeError(f"No se pudo abrir '{ui_filename}'")
    loader = QUiLoader()
    loaded = loader.load(f)
    f.close()
    if loaded is None:
        raise RuntimeError("QUiLoader devolvió None al cargar el .ui")
    loaded.show()
    btn_comp = loaded.findChild(QPushButton, "Comparaciones")
    btn_merge = loaded.findChild(QPushButton, "Mergesort")
    btn_quick = loaded.findChild(QPushButton, "Quicksort")
    status_label = loaded.findChild(QLabel, "label")

    windows = {}
    
    def open_comparaciones():
        mods = ["ui", "sorting_comparison", "sortingcomparison", "app", "comparaciones"]
        classes = ["ComparacionesWindow", "SortingComparison", "ComparisonsWindow", "Comparaciones"]
        scripts = ["ui.py", "app.py", "sorting_comparison.py", "comparaciones.py"]
        for m in mods:
            mod = try_import(m)
            if mod:
                cls = find_window_class(mod, classes)
                if cls:
                    inst = instantiate_and_show(cls)
                    if inst:
                        windows["comparaciones"] = inst
                        if status_label: status_label.setText(f"Abierto {m}.{cls.__name__}")
                        return
                for fn in ("main", "run", "start"):
                    fcall = getattr(mod, fn, None)
                    if callable(fcall):
                        try:
                            fcall()
                            if status_label: status_label.setText(f"Ejecutado {m}.{fn}()")
                            return
                        except Exception:
                            traceback.print_exc()
        for s in scripts:
            if Path(s).exists():
                run_subprocess(s, status_label)
                return
        if status_label:
            status_label.setText("No se pudo abrir Comparaciones (revise nombres).")

    def open_mergesort():
        mods = ["merge_tree_controller", "app", "mergesort", "mergesort_window"]
        classes = ["MergeTreeController", "MergesortWindow", "MergesortController", "Mergesort"]
        scripts = ["merge_tree_controller.py", "app.py", "mergesort.py"]
        for m in mods:
            mod = try_import(m)
            if mod:
                cls = find_window_class(mod, classes)
                if cls:
                    inst = instantiate_and_show(cls)
                    if inst:
                        windows["mergesort"] = inst
                        if status_label: status_label.setText(f"Abierto {m}.{cls.__name__}")
                        return
                for fn in ("main", "run", "start"):
                    fcall = getattr(mod, fn, None)
                    if callable(fcall):
                        try:
                            fcall()
                            if status_label: status_label.setText(f"Ejecutado {m}.{fn}()")
                            return
                        except Exception:
                            traceback.print_exc()
        for s in scripts:
            if Path(s).exists():
                run_subprocess(s, status_label)
                return
        if status_label:
            status_label.setText("No se pudo abrir Mergesort (revise nombres).")

    def open_quicksort():
        mods = ["quicksort", "quicksort_gui", "quick", "quicksort_module"]
        classes = ["QuicksortWindow", "QuicksortGUI", "QuickSortWindow"]
        scripts = ["quicksort.py", "quick.py"]
        for m in mods:
            mod = try_import(m)
            if mod:
                if find_window_class(mod, ["QuicksortGUI"]) or hasattr(mod, "QuicksortGUI"):
                    try:
                        path = Path(mod.__file__).name
                    except Exception:
                        path = None
                    if path and Path(path).exists():
                        run_subprocess(path, status_label)
                        return
                    break
                cls = find_window_class(mod, classes)
                if cls:
                    inst = instantiate_and_show(cls)
                    if inst:
                        windows["quicksort"] = inst
                        if status_label: status_label.setText(f"Abierto {m}.{cls.__name__}")
                        return
        for s in scripts:
            if Path(s).exists():
                run_subprocess(s, status_label)
                return
        if status_label:
            status_label.setText("No se pudo abrir Quicksort (revise nombres).")

    if btn_comp:
        btn_comp.clicked.connect(open_comparaciones)
    if btn_merge:
        btn_merge.clicked.connect(open_mergesort)
    if btn_quick:
        btn_quick.clicked.connect(open_quicksort)

    return loaded

if __name__ == "__main__":
    app = QApplication(sys.argv)
    try:
        ui_widget = load_ui_and_wire("comparacion.ui")
    except Exception as e:
        traceback.print_exc()
        QMessageBox.critical(None, "Error", f"No se pudo cargar 'comparaciones.ui':\n{e}")
        sys.exit(1)
    sys.exit(app.exec())
