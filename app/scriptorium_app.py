import sys
import numpy as np
import pyvista as pv
import SimpleITK as sitk
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QSlider, QRadioButton, 
    QButtonGroup, QGroupBox, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPainter, QPen, QColor, QBrush

class DrawingCanvas(QWidget):
    def __init__(self, grid_z=120, grid_theta=400):
        super().__init__()
        self.grid_z = grid_z
        self.grid_theta = grid_theta
        self.canvas_matrix = np.zeros((self.grid_z, self.grid_theta), dtype=np.float32)
        self.active_ink = 1.0  # 1: Carbon, 2: Iron-Gall, 0: Eraser
        
        self.setFixedSize(600, 180)
        self.setCursor(Qt.CrossCursor)
        self.last_point = None

    def paintEvent(self, event):
        painter = QPainter(self)
        # Draw background substrate color
        painter.fillRect(self.rect(), QColor("#f4ecd8"))
        
        # Draw recorded strokes from matrix
        cell_w = self.width() / self.grid_theta
        cell_h = self.height() / self.grid_z
        
        for z in range(self.grid_z):
            for t in range(self.grid_theta):
                val = self.canvas_matrix[z, t]
                if val > 0:
                    color = QColor("#111111") if val == 1.0 else QColor("#5c2c16")
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
                    self.canvas_matrix[nz, nt] = 0.0 if self.active_ink == 0 else self.active_ink
                    
        self.update()

    def clear(self):
        self.canvas_matrix.fill(0.0)
        self.update()


class ScriptoriumWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Virtual Scriptorium: PySide6 Edition")
        self.resize(700, 550)

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
        self.sub_combo.addItems(["Papyrus", "Palm Leaf", "Parchment"])
        sub_layout.addWidget(self.sub_combo)
        controls_layout.addLayout(sub_layout)

        # Ink radio buttons
        ink_layout = QVBoxLayout()
        ink_layout.addWidget(QLabel("Active Tool:"))
        self.ink_group = QButtonGroup(self)
        
        self.rb_carbon = QRadioButton("Carbon Ink (Z=6)")
        self.rb_carbon.setChecked(True)
        self.ink_group.addButton(self.rb_carbon, 1)
        ink_layout.addWidget(self.rb_carbon)

        self.rb_irongall = QRadioButton("Iron-Gall (Fe)")
        self.ink_group.addButton(self.rb_irongall, 2)
        ink_layout.addWidget(self.rb_irongall)

        self.rb_eraser = QRadioButton("Eraser")
        self.ink_group.addButton(self.rb_eraser, 0)
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

        self.btn_generate = QPushButton("Roll into 3D Scroll & Save .mhd/.raw")
        self.btn_generate.setStyleSheet("background-color: #5cb85c; color: white; font-weight: bold; padding: 6px;")
        self.btn_generate.clicked.connect(self.generate_and_save)
        action_layout.addWidget(self.btn_generate)

        main_layout.addLayout(action_layout)

    def change_ink(self, ink_id):
        self.canvas.active_ink = float(ink_id)

    def update_turns_label(self, value):
        turns = value / 2.0
        self.turns_label.setText(f"Scroll Turns: {turns:.1f}")

    def generate_and_save(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save MHD Phantom", "scriptorium_phantom.mhd", "MetaImage Files (*.mhd)"
        )
        if not file_path:
            return

        try:
            turns = self.turns_slider.value() / 2.0
            grid_z, grid_theta = self.canvas.grid_z, self.canvas.grid_theta
            
            theta = np.linspace(0, 2 * np.pi * turns, grid_theta)
            z = np.linspace(-6.0, 6.0, grid_z)
            Theta, Z = np.meshgrid(theta, z)
            
            R = 0.4 + 1.5 * np.sqrt(Theta / (2 * np.pi))
            X = R * np.cos(Theta)
            Y = R * np.sin(Theta)
            
            structured_grid = pv.StructuredGrid(X, Y, Z)
            # Fix warning and ensure stable surface extraction
            scroll_mesh = structured_grid.extract_surface(algorithm='dataset_surface')
            scroll_mesh.point_data["Elemental_Inks"] = self.canvas.canvas_matrix.flatten(order="F")
            
            vol_dims = (100, 250, 250)
            bounds = scroll_mesh.bounds
            
            uniform_grid = pv.ImageData(
                dimensions=vol_dims,
                spacing=((bounds[1]-bounds[0])/vol_dims[2], (bounds[3]-bounds[2])/vol_dims[1], (bounds[5]-bounds[4])/vol_dims[0]),
                origin=(bounds[0], bounds[2], bounds[4])
            )
            
            voxel_volume = uniform_grid.sample(scroll_mesh).point_data["Elemental_Inks"].reshape(vol_dims)
            
            # Export via SimpleITK
            sitk_image = sitk.GetImageFromArray(voxel_volume.astype(np.float32).transpose(2, 1, 0))
            sitk_image.SetSpacing([uniform_grid.spacing[0], uniform_grid.spacing[1], uniform_grid.spacing[2]])
            sitk_image.SetOrigin([uniform_grid.origin[0], uniform_grid.origin[1], uniform_grid.origin[2]])
            
            sitk.WriteImage(sitk_image, file_path)
            
            QMessageBox.information(
                self, 
                "Success!", 
                f"Successfully generated and exported phantom!\nSaved to:\n{file_path}\n(Companion .raw file created automatically)"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate phantom:\n{str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ScriptoriumWindow()
    window.show()
    sys.exit(app.exec())