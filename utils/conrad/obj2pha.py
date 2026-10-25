import argparse
import trimesh
import numpy as np
import random

def parse_arguments():
    parser = argparse.ArgumentParser(description="Convert a 3D OBJ mesh into a voxelized CONRAD .pha phantom file.")
    parser.add_argument("-i", "--input", required=True, help="Path to the input OBJ mesh file")
    parser.add_argument("-o", "--output", required=True, help="Path to the output .pha phantom file")
    parser.add_argument("-v", "--voxel-size", type=float, default=0.5, help="Voxel size / pitch (default: 0.5)")
    return parser.parse_args()

def voxelize_obj_to_pha(obj_filename, pha_filename, voxel_size):
    # 1. Load the surface mesh OBJ file
    print(f"Loading mesh from {obj_filename}...")
    mesh = trimesh.load(obj_filename)
    
    # 2. Voxelize the mesh
    print(f"Voxelizing mesh with pitch size {voxel_size}...")
    voxelgrid = mesh.voxelized(pitch=voxel_size)
    voxel_matrix = voxelgrid.matrix  # 3D boolean numpy array
    transform = voxelgrid.transform  # Local-to-world transformation matrix
    
    # Define materials with fully capitalized compound names matching your XML files
    materials = [
        {"name": "LAMPBLACKINK"},
        {"name": "IRONGALLINK"},
        {"name": "PAPYRUS"},
        {"name": "PALMLEAF"},
        {"name": "VELLUM"}
    ]
    
    pha_lines = []
    pha_lines.append(f'Phantom "VoxelPhantom"')
    pha_lines.append(f"// CONRAD Voxel Phantom generated from {obj_filename}")
    pha_lines.append(f"// Voxel Size: {voxel_size}\n")
    
    # 3. Find all occupied (True) voxel grid indices
    occupied_indices = np.argwhere(voxel_matrix)
    print(f"Total active voxels found: {len(occupied_indices)}")
    
    # 4. Iterate over each voxel and write it using the exact CONRAD box syntax
    for idx, (i, j, k) in enumerate(occupied_indices):
        # Map voxel grid index to world coordinates
        local_coords = np.array([i, j, k, 1.0])
        world_coords = transform @ local_coords
        
        x = float(world_coords[0])
        y = float(world_coords[1])
        z = float(world_coords[2])
        
        # Randomly select a material (temporary placeholder logic)
        mat = random.choice(materials)
        
        pha_lines.append(f"// Voxel Element {idx+1} - Material: {mat['name']}")
        pha_lines.append(f"{{[ Box: x={x:.4f}; y={y:.4f}; z={z:.4f}; dx={voxel_size}; dy={voxel_size}; dz={voxel_size};]; rho = {mat['name']}; priority = 1;}}\n")
        
    # Write out the final .pha file
    with open(pha_filename, "w") as f:
        f.write("\n".join(pha_lines))
        
    print(f"Successfully generated voxel phantom: {pha_filename}")

if __name__ == "__main__":
    args = parse_arguments()
    voxelize_obj_to_pha(args.input, args.output, args.voxel_size)