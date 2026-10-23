import argparse
import json
import os
import numpy as np
import pyvista as pv

def parse_arguments():
    parser = argparse.ArgumentParser(description="Scriptorium Dual 3D/2D Scroll Viewer")
    parser.add_argument(
        "--input", 
        type=str, 
        default="papyrus_phantom", 
        help="Base filename of the saved phantom (without extension, default: papyrus_phantom)"
    )
    return parser.parse_args()

def main():
    args = parse_arguments()
    json_path = f"{args.input}_metadata.json"
    texture_path = f"{args.input}_unwrapped_texture.npy"
    
    if not os.path.exists(json_path) or not os.path.exists(texture_path):
        print(f"Error: Could not find metadata or texture files for '{args.input}'. Generate it first!")
        return

    print(f"Loading metadata for '{args.input}'...")
    with open(json_path, "r") as f:
        metadata = json.load(f)
        turns = metadata.get("turns", 4.5)
        thickness_px = metadata.get("sheet_thickness_px", 6)

    texture_2d = np.load(texture_path)
    print(f"Loaded 2D unwrapped texture map: shape {texture_2d.shape}")

    # Reconstruct the exact StructuredGrid parametric geometry using pre-allocation
    num_points_z, num_points_theta = texture_2d.shape
    num_layers_r = max(4, thickness_px * 2)

    theta = np.linspace(0, 2 * np.pi * turns, num_points_theta)
    z = np.linspace(-6.0, 6.0, num_points_z)
    r_thickness = np.linspace(0.0, thickness_px * 0.02, num_layers_r)

    Theta_2d, Z_2d = np.meshgrid(theta, z)
    R_base = 0.5 + 0.9 * np.sqrt(Theta_2d / (2 * np.pi))

    X_vol = np.zeros((num_points_z, num_points_theta, num_layers_r), dtype=np.float32)
    Y_vol = np.zeros((num_points_z, num_points_theta, num_layers_r), dtype=np.float32)
    Z_vol = np.zeros((num_points_z, num_points_theta, num_layers_r), dtype=np.float32)
    Scalar_vol = np.zeros((num_points_z, num_points_theta, num_layers_r), dtype=np.float32)

    for i, dr in enumerate(r_thickness):
        R = R_base + dr
        X = R * np.cos(Theta_2d)
        Y = R * np.sin(Theta_2d)
        Z = Z_2d

        if i == num_layers_r - 1:
            scalars_layer = texture_2d
        else:
            scalars_layer = np.full_like(Theta_2d, 1.0, dtype=np.float32)

        X_vol[:, :, i] = X
        Y_vol[:, :, i] = Y
        Z_vol[:, :, i] = Z
        Scalar_vol[:, :, i] = scalars_layer

    structured_grid = pv.StructuredGrid(X_vol, Y_vol, Z_vol)
    structured_grid.point_data["Material"] = Scalar_vol.flatten(order="F")

    # Create a PyVista plotter with 2 viewports (Side-by-side layout)
    plotter = pv.Plotter(shape=(1, 2))
    plotter.set_background("white")

    # --- LEFT WINDOW: 3D Structured Rolled Scroll Volume ---
    plotter.subplot(0, 0)
    plotter.add_text(
        f"3D Rolled Scroll\n(Turns: {turns}, Thickness: {thickness_px}px)", 
        font_size=11, 
        color="black"
    )
    plotter.add_mesh(
        structured_grid,
        scalars="Material",
        cmap=["#d4b583", "#111111", "#5c2c16"], # Papyrus, Carbon, Iron-Gall
        clim=[1.0, 3.0] if texture_2d.max() > 2.0 else [1.0, 2.0],
        n_colors=3,
        show_scalar_bar=False
    )
    plotter.add_axes()

    # --- RIGHT WINDOW: 2D Unwrapped Flat Texture Map ---
    plotter.subplot(0, 1)
    plotter.add_text(
        "2D Unwrapped Writing Canvas\n(Flat Text Layout)", 
        font_size=11, 
        color="black"
    )
    
    nz, ntheta = texture_2d.shape
    plane = pv.Plane(
        center=(ntheta / 2.0, nz / 2.0, 0.0),
        direction=(0.0, 0.0, 1.0),
        i_size=ntheta,
        j_size=nz,
        i_resolution=ntheta - 1,
        j_resolution=nz - 1
    )
    # Use point_data instead of cell_data to match the 72,000 points exactly
    plane.point_data["Texture"] = texture_2d.flatten(order="C")
    plotter.add_mesh(
        plane,
        scalars="Texture",
        cmap=["#d4b583", "#111111", "#5c2c16"],
        clim=[1.0, 3.0] if texture_2d.max() > 2.0 else [1.0, 2.0],
        n_colors=3,
        show_scalar_bar=True
    )
    plotter.view_xy()

    print("Launching dual viewer window...")
    plotter.show()

if __name__ == "__main__":
    main()