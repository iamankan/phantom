import os
import sys
import json
import time
import numpy as np
import pyvista as pv
import SimpleITK as sitk
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QSlider, QGroupBox, QFileDialog, QMessageBox, QInputDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QImage

# Streamlined default elements library (Carbon & Iron-Gall only)
DEFAULT_ELEMENTS = {
    "Carbon Ink": {
        "z_value": 6.0,
        "color": "#111111",
        "code": 2.0
    },
    "Iron-Gall Ink": {
        "z_value": 26.0,
        "color": "#5c2c16",
        "code": 3.0
    }
}

class DrawingCanvas(QWidget):
    def __init__(self, parent_window, grid_z=120, grid_theta=400):
        super().__init__()
        self.grid_z = grid_z
        self.grid_theta = grid_theta
        self.parent_window = parent_window
        
        # Initialize with substrate background (1.0)
        self.canvas_matrix = np.ones((self.grid_z, self.grid_theta), dtype=np.float32)
        self.active_code = 2.0  # Default to first ink
        
        self.setFixedSize(600, 180)
        self.setCursor(Qt.CrossCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#f4ecd8"))
        
        cell_w = self.width() / self.grid_theta
        cell_h = self.height() / self.grid_z
        
        code_to_color = {cfg["code"]: QColor(cfg["color"]) for cfg in self.parent_window.elements_config.values()}

        for z in range(self.grid_z):
            for t in range(self.grid_theta):
                val = self.canvas_matrix[z, t]
                if val > 1.0 and val in code_to_color:
                    painter.fillRect(
                        int(t * cell_w), int(z * cell_h), 
                        max(1, int(cell_w)), max(1, int(cell_h)), 
                        code_to_color[val]
                    )

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.draw_at(event.position().toPoint())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self.draw_at(event.position().toPoint())

    def draw_at(self, pos):
        cell_w = self.width() / self.grid_theta
        cell_h = self.height() / self.grid_z
        
        t_idx = int(pos.x() / cell_w)
        z_idx = int(pos.y() / cell_h)
        
        brush_size = 4
        for dz in range(-brush_size, brush_size + 1):
            for dt in range(-brush_size, brush_size + 1):
                nz, nt = z_idx + dz, t_idx + dt
                if 0 <= nz < self.grid_z and 0 <= nt < self.grid_theta:
                    self.canvas_matrix[nz, nt] = 1.0 if self.active_code == 1.0 else self.active_code
                    
        self.update()

    def clear(self):
        self.canvas_matrix.fill(1.0)
        self.update()


class PhantomStudioProWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Phantom Studio Pro: Advanced Elemental Scroll Synthesizer")
        self.resize(780, 580)

        # 1. Initialize configuration and canvas reference FIRST
        self.elements_config = DEFAULT_ELEMENTS.copy()
        self.canvas = DrawingCanvas(self)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- CONTROLS GROUP ---
        controls_group = QGroupBox("Configuration & Elemental Palette")
        controls_layout = QHBoxLayout(controls_group)

        # Substrate selector
        sub_layout = QVBoxLayout()
        sub_layout.addWidget(QLabel("Substrate:"))
        self.sub_combo = QComboBox()
        self.sub_combo.addItems(["Papyrus (Warm Beige)", "Vellum / Parchment (Cream)", "Palm Leaf (Tan/Fibrous)"])
        sub_layout.addWidget(self.sub_combo)
        controls_layout.addLayout(sub_layout)

        # Dropdown for active element tool selection + Load JSON button
        tool_layout = QVBoxLayout()
        tool_layout.addWidget(QLabel("Active Elemental Tool:"))
        
        tool_select_layout = QHBoxLayout()
        self.element_combo = QComboBox()
        self.populate_dropdown()
        self.element_combo.currentIndexChanged.connect(self.change_tool)
        tool_select_layout.addWidget(self.element_combo)

        self.btn_load_json = QPushButton("Load JSON...")
        self.btn_load_json.setStyleSheet("background-color: #f0ad4e; color: white; font-weight: bold; padding: 4px 8px;")
        self.btn_load_json.clicked.connect(self.load_elements_from_file)
        tool_select_layout.addWidget(self.btn_load_json)

        tool_layout.addLayout(tool_select_layout)
        controls_layout.addLayout(tool_layout)

        # Turns slider
        turns_layout = QVBoxLayout()
        self.turns_label = QLabel("Scroll Turns: 4.0")
        turns_layout.addWidget(self.turns_label)
        self.turns_slider = QSlider(Qt.Horizontal)
        self.turns_slider.setRange(2, 12)  # represents 1.0 to 6.0 (step 0.5)
        self.turns_slider.setValue(8)
        self.turns_slider.valueChanged.connect(self.update_turns_label)
        turns_layout.addWidget(self.turns_slider)
        controls_layout.addLayout(turns_layout)

        main_layout.addWidget(controls_group)

        # --- CANVAS GROUP ---
        canvas_group = QGroupBox("Unrolled Writing Canvas (Click & Drag)")
        canvas_layout = QVBoxLayout(canvas_group)
        canvas_layout.addWidget(self.canvas, alignment=Qt.AlignCenter)
        main_layout.addWidget(canvas_group)

        # --- ACTIONS ---
        action_layout = QHBoxLayout()
        
        self.btn_clear = QPushButton("Clear Canvas")
        self.btn_clear.setStyleSheet("background-color: #d9534f; color: white; font-weight: bold; padding: 6px;")
        self.btn_clear.clicked.connect(self.canvas.clear)
        action_layout.addWidget(self.btn_clear)

        self.btn_generate = QPushButton("Roll into 3D Scroll & Save Pro Bundle")
        self.btn_generate.setStyleSheet("background-color: #5cb85c; color: white; font-weight: bold; padding: 6px;")
        self.btn_generate.clicked.connect(self.generate_and_save)
        action_layout.addWidget(self.btn_generate)

        main_layout.addLayout(action_layout)

        self.last_structured_grid = None

    def populate_dropdown(self):
        self.element_combo.blockSignals(True)
        self.element_combo.clear()
        for name, cfg in self.elements_config.items():
            self.element_combo.addItem(f"{name} (Z={cfg['z_value']})", float(cfg["code"]))
        self.element_combo.addItem("Eraser / Substrate", 1.0)
        self.element_combo.blockSignals(False)
        
        if self.elements_config:
            first_key = list(self.elements_config.keys())[0]
            self.canvas.active_code = self.elements_config[first_key]["code"]

    def load_elements_from_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Elements JSON", "", "JSON Files (*.json);;All Files (*.*)"
        )
        if not file_path:
            return
            
        try:
            with open(file_path, "r") as f:
                loaded_config = json.load(f)
                if isinstance(loaded_config, dict) and len(loaded_config) > 0:
                    self.elements_config = loaded_config
                    self.populate_dropdown()
                    self.canvas.update()
                    QMessageBox.information(self, "Success", f"Successfully loaded elements from:\n{os.path.basename(file_path)}")
                else:
                    raise ValueError("Invalid format inside JSON file.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load elements JSON:\n{str(e)}")

    def change_tool(self, index):
        code = self.element_combo.itemData(index)
        if code is not None:
            self.canvas.active_code = float(code)

    def update_turns_label(self, value):
        turns = value / 2.0
        self.turns_label.setText(f"Scroll Turns: {turns:.1f}")

    def generate_and_save(self):
        turns = self.turns_slider.value() / 2.0
        
        sub_text = self.sub_combo.currentText().split("(")[0].strip().lower().replace(" ", "_")
        default_filename = f"phantom_studio_pro_{sub_text}_turns{turns:.1f}.mhd"

        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Save Phantom Studio Pro Scroll", 
            default_filename, 
            "MetaImage Files (*.mhd);;All Files (*.*)"
        )
        if not file_path:
            return

        # Prompt user for mesh topology choice (Quad vs Triangulated)
        mesh_types = ["Quad Mesh (Quads)", "Triangulated Mesh (Triangles)"]
        mesh_choice, ok = QInputDialog.getItem(
            self, 
            "OBJ Mesh Topology", 
            "Choose export mesh format:", 
            mesh_types, 
            0, 
            False
        )
        if not ok:
            return
        is_triangulated = ("Triangulated" in mesh_choice)

        file_path = os.path.abspath(file_path)
        parent_dir = os.path.dirname(file_path)
        base_name = os.path.basename(file_path)
        
        if base_name.endswith(".mhd"):
            base_name = base_name[:-4]
        elif "." in base_name:
            base_name = base_name.rsplit(".", 1)[0]

        # --- CREATE UNIQUE UTC TIMESTAMP FOLDER ---
        utc_sec = int(time.time())
        export_folder_name = f"{base_name}_utc{utc_sec}"
        export_dir = os.path.join(parent_dir, export_folder_name)
        os.makedirs(export_dir, exist_ok=True)

        mhd_path = os.path.join(export_dir, f"{base_name}.mhd")
        json_path = os.path.join(export_dir, f"{base_name}_metadata.json")
        texture_path = os.path.join(export_dir, f"{base_name}_unwrapped_texture.npy")
        zmap_path = os.path.join(export_dir, f"{base_name}_elemental_zmap.npy")
        
        obj_path = os.path.join(export_dir, f"{base_name}.obj")
        mtl_path = os.path.join(export_dir, f"{base_name}.mtl")
        mtl_filename = f"{base_name}.mtl"
        png_texture_path = os.path.join(export_dir, f"{base_name}_unwrapped_texture.png")

        try:
            sheet_thickness_px = 6
            grid_z, grid_theta = self.canvas.grid_z, self.canvas.grid_theta
            
            theta = np.linspace(0, 2 * np.pi * turns, grid_theta)
            z = np.linspace(-6.0, 6.0, grid_z)
            r_thickness = np.linspace(0.0, sheet_thickness_px * 0.02, max(4, sheet_thickness_px // 2))

            Theta_2d, Z_2d = np.meshgrid(theta, z)
            R_base = 0.5 + 0.9 * np.sqrt(Theta_2d / (2 * np.pi))

            all_X, all_Y, all_Z, all_scalars = [], [], [], []

            for i, dr in enumerate(r_thickness):
                R = R_base + dr
                X = R * np.cos(Theta_2d)
                Y = R * np.sin(Theta_2d)
                Z = Z_2d

                if i == len(r_thickness) - 1:
                    scalars_layer = self.canvas.canvas_matrix
                else:
                    scalars_layer = np.full_like(Theta_2d, 1.0, dtype=np.float32)

                all_X.append(X)
                all_Y.append(Y)
                all_Z.append(Z)
                all_scalars.append(scalars_layer)

            X_vol = np.transpose(np.array(all_X), (1, 2, 0))
            Y_vol = np.transpose(np.array(all_Y), (1, 2, 0))
            Z_vol = np.transpose(np.array(all_Z), (1, 2, 0))
            Scalar_vol = np.transpose(np.array(all_scalars), (1, 2, 0))

            structured_grid = pv.StructuredGrid(X_vol, Y_vol, Z_vol)
            structured_grid.point_data["Material"] = Scalar_vol.flatten(order="F")
            self.last_structured_grid = structured_grid

            bounds = structured_grid.bounds
            voxel_dims = (150, 300, 300)
            uniform_grid = pv.ImageData(
                dimensions=voxel_dims,
                spacing=((bounds[1]-bounds[0])/voxel_dims[2], 
                         (bounds[3]-bounds[2])/voxel_dims[1], 
                         (bounds[5]-bounds[4])/voxel_dims[0]),
                origin=(bounds[0], bounds[2], bounds[4])
            )
            sampled_grid = uniform_grid.sample(structured_grid)
            
            voxel_volume_3d = np.round(np.nan_to_num(sampled_grid.point_data["Material"].reshape(voxel_dims), nan=1.0))
            max_code = max([cfg["code"] for cfg in self.elements_config.values()] + [1.0])
            voxel_volume_3d = np.clip(voxel_volume_3d, 1.0, max_code)

            sitk_image = sitk.GetImageFromArray(voxel_volume_3d.astype(np.float32))
            sitk_image.SetSpacing(uniform_grid.spacing)
            sitk_image.SetOrigin(uniform_grid.origin)
            sitk.WriteImage(sitk_image, mhd_path)

            zmap_conditions = []
            zmap_choices = []
            for cfg in self.elements_config.values():
                zmap_conditions.append(self.canvas.canvas_matrix == cfg["code"])
                zmap_choices.append(cfg["z_value"])

            zmap_matrix = np.select(
                zmap_conditions,
                zmap_choices,
                default=0.0
            ).astype(np.float32)

            texture_conditions = []
            texture_choices = []
            num_elements = len(self.elements_config)
            for idx, cfg in enumerate(self.elements_config.values()):
                texture_conditions.append(self.canvas.canvas_matrix == cfg["code"])
                texture_choices.append(float(idx + 1) / num_elements)

            texture_display_matrix = np.select(
                texture_conditions,
                texture_choices,
                default=0.0
            ).astype(np.float32)

            metadata = {
                "generated_by": "phantom_studio_pro",
                "studio_name": "Phantom Studio Pro",
                "custom_base_name": base_name,
                "utc_timestamp_sec": utc_sec,
                "turns": turns,
                "sheet_thickness_px": sheet_thickness_px,
                "voxel_dimensions": list(voxel_dims),
                "formula": "R = 0.5 + 0.9 * sqrt(Theta / (2 * pi))",
                "substrate": self.sub_combo.currentText(),
                "loaded_elements_config": self.elements_config,
                "mesh_topology": "Triangles" if is_triangulated else "Quads"
            }
            with open(json_path, "w") as f:
                json.dump(metadata, f, indent=4)
                
            np.save(texture_path, texture_display_matrix)
            np.save(zmap_path, zmap_matrix)

            # --- EXPORT PNG TEXTURE FOR MTL MAPPING ---
            img = QImage(grid_theta, grid_z, QImage.Format_RGB32)
            code_to_qcolor = {cfg["code"]: QColor(cfg["color"]) for cfg in self.elements_config.values()}
            default_sub_color = QColor("#f4ecd8")
            
            for z in range(grid_z):
                for t in range(grid_theta):
                    val = self.canvas.canvas_matrix[z, t]
                    if val > 1.0 and val in code_to_qcolor:
                        img.setPixelColor(t, z, code_to_qcolor[val])
                    else:
                        img.setPixelColor(t, z, default_sub_color)
            img.save(png_texture_path)

            # --- EXPORT WAVEFRONT OBJ & MTL ---
            X_outer = X_vol[:, :, -1]
            Y_outer = Y_vol[:, :, -1]
            Z_outer = Z_vol[:, :, -1]

            with open(mtl_path, "w") as f_mtl:
                f_mtl.write("# Phantom Studio Pro Material File\n")
                f_mtl.write("newmtl ScrollMaterial\n")
                f_mtl.write("Kd 1.0 1.0 1.0\n")
                f_mtl.write(f"map_Kd {base_name}_unwrapped_texture.png\n")

            with open(obj_path, "w") as f_obj:
                f_obj.write(f"mtllib {mtl_filename}\n")
                f_obj.write("usematerial ScrollMaterial\n")
                
                # 1. Vertices (v)
                for z_idx in range(grid_z):
                    for t_idx in range(grid_theta):
                        f_obj.write(f"v {X_outer[z_idx, t_idx]:.6f} {Y_outer[z_idx, t_idx]:.6f} {Z_outer[z_idx, t_idx]:.6f}\n")
                        
                # 2. UV Coordinates (vt)
                for z_idx in range(grid_z):
                    v_coord = 1.0 - (z_idx / (grid_z - 1))
                    for t_idx in range(grid_theta):
                        u_coord = t_idx / (grid_theta - 1)
                        f_obj.write(f"vt {u_coord:.6f} {v_coord:.6f}\n")
                        
                # 3. Faces (Quads or Triangles)
                for z_idx in range(grid_z - 1):
                    for t_idx in range(grid_theta - 1):
                        p0 = z_idx * grid_theta + t_idx + 1
                        p1 = z_idx * grid_theta + (t_idx + 1) + 1
                        p2 = (z_idx + 1) * grid_theta + (t_idx + 1) + 1
                        p3 = (z_idx + 1) * grid_theta + t_idx + 1
                        
                        if is_triangulated:
                            f_obj.write(f"f {p0}/{p0} {p1}/{p1} {p2}/{p2}\n")
                            f_obj.write(f"f {p0}/{p0} {p2}/{p2} {p3}/{p3}\n")
                        else:
                            f_obj.write(f"f {p0}/{p0} {p1}/{p1} {p2}/{p2} {p3}/{p3}\n")

            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Success!")
            msg_box.setText(
                f"Phantom Studio Pro exported to unique folder:\n[{export_folder_name}]\n\n"
                f"• {base_name}.mhd (+ .raw)\n"
                f"• {base_name}.obj ({mesh_choice}) & .mtl\n"
                f"• {base_name}_unwrapped_texture.png (.npy)\n"
                f"• {base_name}_elemental_zmap.npy\n"
                f"• {base_name}_metadata.json"
            )
            btn_view = msg_box.addButton("View Rolled Artifact in 3D", QMessageBox.AcceptRole)
            btn_ok = msg_box.addButton(QMessageBox.Ok)
            msg_box.exec()

            if msg_box.clickedButton() == btn_view:
                self.view_3d_artifact(base_name, turns)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate pro phantom:\n{str(e)}")

    def view_3d_artifact(self, base_name, turns):
        if self.last_structured_grid is None:
            return
            
        codes = sorted(list(set([cfg["code"] for cfg in self.elements_config.values()])))
        min_code = 1.0
        max_code = max(codes) if codes else 3.0
        
        cmap_list = ["#d4b583"]
        for code in codes:
            for cfg in self.elements_config.values():
                if cfg["code"] == code:
                    cmap_list.append(cfg["color"])

        plotter = pv.Plotter()
        plotter.set_background("white")
        plotter.add_text(f"Phantom Studio Pro: {base_name} ({turns} turns)", font_size=12, color="black")
        plotter.add_mesh(
            self.last_structured_grid,
            scalars="Material",
            cmap=cmap_list,
            clim=[min_code, max_code + (1.0 if len(codes)>0 else 0)],
            interpolate_before_map=False,
            show_scalar_bar=False
        )
        plotter.add_axes()
        plotter.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PhantomStudioProWindow()
    window.show()
    sys.exit(app.exec())