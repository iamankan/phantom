import argparse
import json
import numpy as np
import SimpleITK as sitk
import pyvista as pv

def parse_arguments():
    parser = argparse.ArgumentParser(description="Generate rolled scroll via direct structured grid.")
    parser.add_argument("--turns", type=float, default=4.5, help="Number of spiral turns")
    parser.add_argument("--sheet-thickness-px", type=int, default=6, help="Sheet thickness in pixels")
    parser.add_argument("--output", type=str, default="papyrus_phantom", help="Base filename")
    return parser.parse_args()

def main():
    args = parse_arguments()
    print(f"Generating rolled scroll: {args.turns} turns, {args.sheet_thickness_px}px thickness...")

    num_points_theta = 600
    num_points_z = 120
    num_layers_r = max(4, args.sheet_thickness_px * 2)

    theta = np.linspace(0, 2 * np.pi * args.turns, num_points_theta)
    z = np.linspace(-6.0, 6.0, num_points_z)
    r_thickness = np.linspace(0.0, args.sheet_thickness_px * 0.02, num_layers_r)

    Theta_2d, Z_2d = np.meshgrid(theta, z)
    R_base = 0.5 + 0.9 * np.sqrt(Theta_2d / (2 * np.pi))

    # 2D Texture Pattern (1 = Papyrus, 2 = Carbon Ink, 3 = Iron-Gall Ink)
    ink_pattern = np.full_like(Theta_2d, 1, dtype=np.float32)
    is_background = ((Theta_2d - 8) % 1.0 < 0.1) & ((Z_2d - 8) % 1.0 < 0.1)
    is_iron = (np.floor(Theta_2d * 2 / np.pi) % 2 == 0)
    
    ink_pattern[~is_background & is_iron] = 3  
    ink_pattern[~is_background & ~is_iron] = 2 
    ink_pattern[is_background] = 1             

    all_X, all_Y, all_Z, all_scalars = [], [], [], []

    for i, dr in enumerate(r_thickness):
        R = R_base + dr
        X = R * np.cos(Theta_2d)
        Y = R * np.sin(Theta_2d)
        Z = Z_2d

        # Apply the ink pattern exclusively to the outermost layer (last radial step)
        if i == len(r_thickness) - 1:
            scalars_layer = ink_pattern
        else:
            scalars_layer = np.full_like(Theta_2d, 1, dtype=np.float32)

        all_X.append(X)
        all_Y.append(Y)
        all_Z.append(Z)
        all_scalars.append(scalars_layer)

    # Build True Structured Grid (Shape: [theta, z, r])
    X_vol = np.transpose(np.array(all_X), (1, 2, 0))
    Y_vol = np.transpose(np.array(all_Y), (1, 2, 0))
    Z_vol = np.transpose(np.array(all_Z), (1, 2, 0))
    Scalar_vol = np.transpose(np.array(all_scalars), (1, 2, 0))

    structured_grid = pv.StructuredGrid(X_vol, Y_vol, Z_vol)
    structured_grid.point_data["Material"] = Scalar_vol.flatten(order="F")

    # Save outputs for metadata and dual viewer
    mhd_path = f"{args.output}.mhd"
    json_path = f"{args.output}_metadata.json"
    texture_path = f"{args.output}_unwrapped_texture.npy"

    # Export uniform sampling for .mhd compatibility
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
    voxel_volume_3d = np.nan_to_num(sampled_grid.point_data["Material"].reshape(voxel_dims), nan=1.0)

    sitk_image = sitk.GetImageFromArray(voxel_volume_3d.astype(np.float32))
    sitk_image.SetSpacing(uniform_grid.spacing)
    sitk_image.SetOrigin(uniform_grid.origin)
    sitk.WriteImage(sitk_image, mhd_path)

    metadata = {
        "turns": args.turns,
        "sheet_thickness_px": args.sheet_thickness_px,
        "voxel_dimensions": list(voxel_dims),
        "formula": "R = 0.5 + 0.9 * sqrt(Theta / (2 * pi))"
    }
    with open(json_path, "w") as f:
        json.dump(metadata, f, indent=4)
        
    np.save(texture_path, ink_pattern)
    print(f"Saved direct structural scroll to {mhd_path}")

    # Launch PyVista Viewer directly on the structured geometry
    plotter = pv.Plotter()
    plotter.set_background("white")
    plotter.add_text(f"Direct Structured Scroll ({args.turns} turns)", font_size=12, color="black")
    
    plotter.add_mesh(
        structured_grid,
        scalars="Material",
        cmap=["#d4b583", "#111111", "#5c2c16"],
        clim=[1, 3],
        n_colors=3,
        show_scalar_bar=True
    )
    plotter.add_axes()
    plotter.show()

if __name__ == "__main__":
    main()