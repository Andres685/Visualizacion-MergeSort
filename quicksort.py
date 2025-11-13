import tkinter as tk
from tkinter import messagebox

def build_steps_and_tree(lista):
    steps = []
    nodes = [] 
    node_counter = 0

    def new_node_id():
        nonlocal node_counter
        node_counter += 1
        return node_counter

    def qs(lst, nivel, parent_id=None):
        node_id = new_node_id()

        nodes.append({
            "id": node_id,
            "parent": parent_id,
            "nivel": nivel,
            "lista": lst[:]
        })

        steps.append({
            "tipo": "inicio",
            "nivel": nivel,
            "lista": lst[:],
            "node_id": node_id
        })

        if len(lst) <= 1:
            steps.append({
                "tipo": "base",
                "nivel": nivel,
                "lista": lst[:],
                "node_id": node_id
            })
            return lst

        pivote = lst[-1]  
        menores = []
        mayores = []

        for e in lst[:-1]:
            if e < pivote:
                menores.append(e)
            else:
                mayores.append(e)

        steps.append({
            "tipo": "particion",
            "nivel": nivel,
            "lista": lst[:],
            "pivote": pivote,
            "menores": menores[:],
            "mayores": mayores[:],
            "node_id": node_id
        })

        menores_ord = qs(menores, nivel + 1, parent_id=node_id)
        mayores_ord = qs(mayores, nivel + 1, parent_id=node_id)

        res = menores_ord + [pivote] + mayores_ord

        steps.append({
            "tipo": "resultado",
            "nivel": nivel,
            "lista": res[:],
            "node_id": node_id
        })

        return res

    qs(lista, 0, None)
    return steps, nodes

class QuicksortGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Visualización Quicksort clásico (lista + árbol)")

        self.steps = []
        self.nodes = []
        self.node_positions = {}
        self.index = 0

        frame_input = tk.Frame(root, padx=10, pady=10)
        frame_input.pack(fill="x")

        tk.Label(frame_input, text="Introduce números separados por comas:").pack(anchor="w")
        self.entry = tk.Entry(frame_input, width=50)
        self.entry.insert(0, "8, 3, 1, 7, 0, 10, 2") 
        self.entry.pack(anchor="w", pady=5)

        self.btn_generar = tk.Button(frame_input, text="Generar pasos", command=self.generar_pasos)
        self.btn_generar.pack(anchor="w")

        frame_main = tk.Frame(root, padx=10, pady=10)
        frame_main.pack(fill="both", expand=True)

        frame_view = tk.Frame(frame_main, padx=10, pady=10, relief="groove", borderwidth=2)
        frame_view.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        self.label_paso = tk.Label(frame_view, text="Paso: -", font=("Arial", 12, "bold"))
        self.label_paso.pack(anchor="w")

        self.label_nivel = tk.Label(frame_view, text="Nivel de recursión: -")
        self.label_nivel.pack(anchor="w")

        self.label_lista = tk.Label(frame_view, text="Lista: -", font=("Consolas", 12))
        self.label_lista.pack(anchor="w", pady=5)

        self.label_pivote = tk.Label(frame_view, text="Pivote: -")
        self.label_pivote.pack(anchor="w")

        self.label_menores = tk.Label(frame_view, text="Menores: -")
        self.label_menores.pack(anchor="w")

        self.label_mayores = tk.Label(frame_view, text="Mayores: -")
        self.label_mayores.pack(anchor="w")

        self.label_mensaje = tk.Label(frame_view, text="", justify="left", wraplength=400)
        self.label_mensaje.pack(anchor="w", pady=10)

        frame_tree = tk.Frame(frame_main, padx=10, pady=10, relief="groove", borderwidth=2)
        frame_tree.pack(side="right", fill="both", expand=True, padx=5, pady=5)

        tk.Label(frame_tree, text="Árbol de llamadas de Quicksort", font=("Arial", 11, "bold")).pack(anchor="n")

        self.canvas = tk.Canvas(frame_tree, width=600, height=400, bg="white")
        self.canvas.pack(fill="both", expand=True, pady=5)

        frame_nav = tk.Frame(root, padx=10, pady=10)
        frame_nav.pack()

        self.btn_anterior = tk.Button(frame_nav, text="⟨ Anterior", command=self.anterior_paso, state="disabled")
        self.btn_anterior.grid(row=0, column=0, padx=5)

        self.btn_siguiente = tk.Button(frame_nav, text="Siguiente ⟩", command=self.siguiente_paso, state="disabled")
        self.btn_siguiente.grid(row=0, column=1, padx=5)

        self.btn_reiniciar = tk.Button(frame_nav, text="Reiniciar", command=self.reiniciar, state="disabled")
        self.btn_reiniciar.grid(row=0, column=2, padx=5)

    def parse_lista(self):
        texto = self.entry.get().strip()
        if not texto:
            raise ValueError("Debes introducir al menos un número.")
        partes = texto.split(",")
        lista = []
        for p in partes:
            p = p.strip()
            if not p:
                continue
            try:
                lista.append(int(p))
            except ValueError:
                raise ValueError(f"'{p}' no es un número entero válido.")
        if not lista:
            raise ValueError("No se encontró ningún número válido.")
        return lista

    def generar_pasos(self):
        try:
            lista = self.parse_lista()
        except ValueError as e:
            messagebox.showerror("Error en la entrada", str(e))
            return

        self.steps, self.nodes = build_steps_and_tree(lista)
        self.index = 0

        self.compute_tree_layout()
        self.draw_tree(current_node_id=self.steps[0].get("node_id"))

        self.btn_anterior.config(state="disabled")
        self.btn_siguiente.config(state="normal")
        self.btn_reiniciar.config(state="normal")

        self.mostrar_paso()

    def mostrar_paso(self):
        if not self.steps:
            return
        paso = self.steps[self.index]
        total = len(self.steps)

        self.label_paso.config(text=f"Paso {self.index + 1} de {total}")

        nivel = paso.get("nivel", 0)
        self.label_nivel.config(text=f"Nivel de recursión: {nivel}")

        self.label_lista.config(text=f"Lista: {paso.get('lista', [])}")

        if paso["tipo"] == "particion":
            self.label_pivote.config(text=f"Pivote: {paso.get('pivote')}")
            self.label_menores.config(text=f"Menores: {paso.get('menores')}")
            self.label_mayores.config(text=f"Mayores: {paso.get('mayores')}")
        else:
            self.label_pivote.config(text="Pivote: -")
            self.label_menores.config(text="Menores: -")
            self.label_mayores.config(text="Mayores: -")

        tipo = paso["tipo"]
        if tipo == "inicio":
            msg = "📦 Nueva llamada de Quicksort sobre esta sublista."
        elif tipo == "base":
            msg = "✅ Caso base: la sublista tiene 0 o 1 elemento, ya está ordenada."
        elif tipo == "particion":
            msg = ("✂ Se ha elegido el pivote y se ha dividido la lista en dos:\n"
                   "   • 'Menores' contiene los valores más pequeños que el pivote.\n"
                   "   • 'Mayores' contiene los valores mayores o iguales al pivote.\n"
                   "   Después se ordenará cada sublista por separado.")
        elif tipo == "resultado":
            msg = "🔁 Resultado parcial: esta sublista ya está ordenada."
        else:
            msg = ""

        self.label_mensaje.config(text=msg)

        # 🔹 CAMBIO IMPORTANTE:
        # si el paso es 'resultado' o 'base', actualizamos la lista del nodo
        if tipo in ("resultado", "base"):  # ← CAMBIO
            node_id = paso.get("node_id")
            if node_id is not None:
                for n in self.nodes:
                    if n["id"] == node_id:
                        n["lista"] = paso.get("lista", n["lista"])
                        break

        current_node_id = paso.get("node_id")
        self.draw_tree(current_node_id=current_node_id)

        self.btn_anterior.config(state="normal" if self.index > 0 else "disabled")
        self.btn_siguiente.config(state="normal" if self.index < total - 1 else "disabled")

    def siguiente_paso(self):
        if self.index < len(self.steps) - 1:
            self.index += 1
            self.mostrar_paso()

    def anterior_paso(self):
        if self.index > 0:
            self.index -= 1
            self.mostrar_paso()

    def reiniciar(self):
        if not self.steps:
            return
        self.index = 0
        self.mostrar_paso()

    def compute_tree_layout(self):
        self.node_positions = {}
        if not self.nodes:
            return

        niveles = {}
        max_nivel = 0
        for node in self.nodes:
            nivel = node["nivel"]
            max_nivel = max(max_nivel, nivel)
            niveles.setdefault(nivel, []).append(node)

        width = 600
        level_height = 80

        for nivel in sorted(niveles.keys()):
            nodos_nivel = niveles[nivel]
            count = len(nodos_nivel)
            if count == 0:
                continue
            y = 40 + nivel * level_height
            spacing = width // (count + 1)
            for i, node in enumerate(nodos_nivel, start=1):
                x = spacing * i
                self.node_positions[node["id"]] = (x, y)

    def draw_tree(self, current_node_id=None):
        self.canvas.delete("all")
        if not self.nodes or not self.node_positions:
            return

        for node in self.nodes:
            node_id = node["id"]
            parent_id = node["parent"]
            if parent_id is None:
                continue
            if node_id not in self.node_positions or parent_id not in self.node_positions:
                continue
            x, y = self.node_positions[node_id]
            px, py = self.node_positions[parent_id]
            self.canvas.create_line(px, py + 20, x, y - 20)

        for node in self.nodes:
            node_id = node["id"]
            x, y = self.node_positions[node_id]
            r = 24 
            is_current = (node_id == current_node_id)

            fill = "lightblue" if is_current else "white"
            outline = "blue" if is_current else "black"
            width = 2 if is_current else 1

            self.canvas.create_oval(x - r, y - r, x + r, y + r,
                                    fill=fill, outline=outline, width=width)

            texto = ",".join(str(v) for v in node["lista"])
            self.canvas.create_text(x, y, text=texto, font=("Consolas", 8))

if __name__ == "__main__":
    root = tk.Tk()
    app = QuicksortGUI(root)
    root.mainloop()
