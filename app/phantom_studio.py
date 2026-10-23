import os
import sys
import json
import numpy as np
import pyvista as pv
import SimpleITK as sitk
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QSlider, QRadioButton, 
    QButtonGroup, QGroupBox, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor

class DrawingCanvas(QWidget):
    def __init__(self, grid_z=120, grid_theta=400):
        super().__init__()
        self.grid_z = grid_z
        self.grid_theta = grid_theta
        # Initialize with substrate background (1.0)
        self.canvas_matrix = np.ones((self.grid_z, self.grid_theta), dtype=np.float32)
        self.active_ink = 2.0  # 2: Carbon Ink, 3: Iron-Gall, 1.0: Substrate/Eraser
        
        self.setFixedSize(600, 180)
        self.setCursor(Qt.CrossCursor)
        self.last_point = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#f4ecd8"))
        
        cell_w = self.width() / self.grid_theta
        cell_h = self.height() / self.grid_z
        
        for z in range(self.grid_z):
            for t in range(self.grid_theta):
                val = self.canvas_matrix[z, t]
                if val > 1.0:
                    color = QColor("#111111") if val == 2.0 else QColor("#5c2c16")
                    painter.fillRect(int(t * cell_w), int(z * cell_h), max(1, int(cell_w)), max(1, int(cell_h)), color)

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
                    # Eraser sets back to substrate default (1.0)
                    self.canvas_matrix[nz, nt] = 1.0 if self.active_ink == 1.0 else self.active_ink
                    
        self.update()

    def clear(self):
        self.canvas_matrix.fill(1.0)
        self.update()


class PhantomStudioWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Phantom Studio: 2D Writing Canvas & 3D Roll Generator")
        self.resize(700, 580)

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

        # Ink radio buttons
        ink_layout = QVBoxLayout()
        ink_layout.addWidget(QLabel("Active Tool:"))
        self.ink_group = QButtonGroup(self)
        
        self.rb_carbon = QRadioButton("Carbon Ink (Matte Black)")
        self.rb_carbon.setChecked(True)
        self.ink_group.addButton(self.rb_carbon, 2)
        ink_layout.addWidget(self.rb_carbon)

        self.rb_irongall = QRadioButton("Iron-Gall (Dark Brown)")
        self.ink_group.addButton(self.rb_irongall, 3)
        ink_layout.addWidget(self.rb_irongall)

        self.rb_eraser = QRadioButton("Eraser / Substrate")
        self.ink_group.addButton(self.rb_eraser, 1)
        ink_layout.addWidget(self.rb_eraser)
        
        self.ink_group.idClicked.connect(self.change_ink)
        controls_layout.addLayout(ink_layout)

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
        self.canvas = DrawingCanvas()
        canvas_layout.addWidget(self.canvas, alignment=Qt.AlignCenter)
        main_layout.addWidget(canvas_group)

        # --- ACTIONS ---
        action_layout = QHBoxLayout()
        
        self.btn_clear = QPushButton("Clear Canvas")
        self.btn_clear.setStyleSheet("background-color: #d9534f; color: white; font-weight: bold; padding: 6px;")
        self.btn_clear.clicked.connect(self.canvas.clear)
        action_layout.addWidget(self.btn_clear)

        self.btn_generate = QPushButton("Roll into 3D Scroll & Save with Metadata")
        self.btn_generate.setStyleSheet("background-color: #5cb85c; color: white; font-weight: bold; padding: 6px;")
        self.btn_generate.clicked.connect(self.generate_and_save)
        action_layout.addWidget(self.btn_generate)

        main_layout.addLayout(action_layout)

        self.last_structured_grid = None

    def change_ink(self, ink_id):
        self.canvas.active_ink = float(ink_id)

    def update_turns_label(self, value):
        turns = value / 2.0
        self.turns_label.setText(f"Scroll Turns: {turns:.1f}")

    def generate_and_save(self):
        turns = self.turns_slider.value() / 2.0
        
        sub_text = self.sub_combo.currentText().split("(")[0].strip().lower().replace(" ", "_")
        default_filename = f"phantom_studio_{sub_text}_turns{turns:.1f}.mhd"

        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Save Phantom Studio Scroll", 
            default_filename, 
            "MetaImage Files (*.mhd);;All Files (*.*)"
        )
        if not file_path:
            return

        file_path = os.path.abspath(file_path)
        directory = os.path.dirname(file_path)
        base_name = os.path.basename(file_path)
        
        if base_name.endswith(".mhd"):
            base_name = base_name[:-4]
        elif "." in base_name:
            base_name = base_name.rsplit(".", 1)[0]

        mhd_path = os.path.join(directory, f"{base_name}.mhd")
        json_path = os.path.join(directory, f"{base_name}_metadata.json")
        texture_path = os.path.join(directory, f"{base_name}_unwrapped_texture.npy")
        zmap_path = os.path.join(directory, f"{base_name}_elemental_zmap.npy")

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
            voxel_volume_3d = np.clip(voxel_volume_3d, 1.0, 3.0)

            sitk_image = sitk.GetImageFromArray(voxel_volume_3d.astype(np.float32))
            sitk_image.SetSpacing(uniform_grid.spacing)
            sitk_image.SetOrigin(uniform_grid.origin)
            sitk.WriteImage(sitk_image, mhd_path)

            # Elemental Z-map: Store ONLY atomic numbers for ink strokes, 0.0 for background substrate
            zmap_matrix = np.select(
                [
                    self.canvas.canvas_matrix == 3.0,
                    self.canvas.canvas_matrix == 2.0
                ],
                [26.0, 6.0],
                default=0.0
            ).astype(np.float32)

            # High-contrast texture array for viewing (Background = 0.0, Carbon = 0.5, Iron-Gall = 1.0)
            texture_display_matrix = np.select(
                [
                    self.canvas.canvas_matrix == 3.0,
                    self.canvas.canvas_matrix == 2.0,
                ],
                [1.0, 0.5],
                default=0.0
            ).astype(np.float32)

            metadata = {
                "generated_by": "phantom_studio",
                "studio_name": "Phantom Studio",
                "custom_base_name": base_name,
                "turns": turns,
                "sheet_thickness_px": sheet_thickness_px,
                "voxel_dimensions": list(voxel_dims),
                "formula": "R = 0.5 + 0.9 * sqrt(Theta / (2 * pi))",
                "substrate": self.sub_combo.currentText(),
                "element_mapping": {
                    "background": 0.0,
                    "carbon_ink": 6.0,
                    "iron_gall_ink": 26.0
                }
            }
            with open(json_path, "w") as f:
                json.dump(metadata, f, indent=4)
                
            np.save(texture_path, texture_display_matrix)
            np.save(zmap_path, zmap_matrix)

            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Success!")
            msg_box.setText(
                f"Phantom Studio exported successfully using base name: '{base_name}'\n\n"
                f"• {base_name}.mhd (+ .raw)\n"
                f"• {base_name}_metadata.json\n"
                f"• {base_name}_unwrapped_texture.npy\n"
                f"• {base_name}_elemental_zmap.npy (Ink Z-values only)"
            )
            btn_view = msg_box.addButton("View Rolled Artifact in 3D", QMessageBox.AcceptRole)
            btn_ok = msg_box.addButton(QMessageBox.Ok)
            msg_box.exec()

            if msg_box.clickedButton() == btn_view:
                self.view_3d_artifact(base_name, turns)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate phantom:\n{str(e)}")

    def view_3d_artifact(self, base_name, turns):
        if self.last_structured_grid is None:
            return
        plotter = pv.Plotter()
        plotter.set_background("white")
        plotter.add_text(f"Phantom Studio: {base_name} ({turns} turns)", font_size=12, color="black")
        plotter.add_mesh(
            self.last_structured_grid,
            scalars="Material",
            cmap=["#d4b583", "#111111", "#5c2c16"],
            clim=[1.0, 3.0],
            n_colors=3,
            interpolate_before_map=False,
            show_scalar_bar=False
        )
        plotter.add_axes()
        plotter.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PhantomStudioWindow()
    window.show()
    sys.exit(app.exec())