import argparse
import subprocess
import tempfile
import os
import re
import numpy as np

def parse_arguments():
    parser = argparse.ArgumentParser(description="Convert an OpenSCAD .scad file into a CONRAD .pha primitive phantom file.")
    parser.add_argument("-i", "--input", required=True, help="Path to the input .scad file")
    parser.add_argument("-o", "--output", required=True, help="Path to the output .pha phantom file")
    parser.add_argument("-m", "--material", default="BONE", help="Default material name for rho (default: BONE)")
    parser.add_argument("--phantom-name", default="OpenSCAD_Phantom", help="Name of the phantom in the .pha file")
    return parser.parse_args()

def parse_csg_to_pha(csg_text, default_material):
    pha_lines = []
    lines = csg_text.splitlines()
    
    # Track matrix transformations hierarchically or sequentially
    # OpenSCAD CSG exports use multimatrix or translate/rotate statements
    current_matrix = np.identity(4)
    matrix_stack = []
    
    for line in lines:
        line = line.strip()
        
        # Handle block entries/exits in CSG tree
        if "{" in line:
            matrix_stack.append(np.copy(current_matrix))
        if "}" in line and matrix_stack:
            current_matrix = matrix_stack.pop()
            
        # Parse multimatrix if present in CSG
        m_match = re.search(r'multimatrix\s*\(\s*\[\s*\[([^\]]+)\]\s*,\s*\[([^\]]+)\]\s*,\s*\[([^\]]+)\]\s*\]\s*\)', line)
        if m_match:
            try:
                row0 = [float(x) for x in m_match.group(1).split(',')]
                row1 = [float(x) for x in m_match.group(2).split(',')]
                row2 = [float(x) for x in m_match.group(3).split(',')]
                m = np.identity(4)
                m[0, :4] = row0
                m[1, :4] = row1
                m[2, :4] = row2
                current_matrix = current_matrix @ m
            except Exception:
                pass

        # Fallback regex for direct translate
        trans_match = re.search(r'translate\s*\(\s*v?\s*=\s*\[\s*([-\d\.]+),\s*([-\d\.]+),\s*([-\d\.]+)\]\s*\)', line)
        if trans_match:
            tx, ty, tz = float(trans_match.group(1)), float(trans_match.group(2)), float(trans_match.group(3))
            t_mat = np.identity(4)
            t_mat[0, 3] = tx
            t_mat[1, 3] = ty
            t_mat[2, 3] = tz
            current_matrix = current_matrix @ t_mat
            continue

        # Parse cube -> CONRAD Box using transformed origin coordinates
        cube_match = re.search(r'cube\s*\(\s*size\s*=\s*\[\s*([-\d\.]+),\s*([-\d\.]+),\s*([-\d\.]+)\]', line)
        if cube_match:
            dx, dy, dz = float(cube_match.group(1)), float(cube_match.group(2)), float(cube_match.group(3))
            
            # Extract world position from current transformation matrix
            origin = current_matrix @ np.array([0.0, 0.0, 0.0, 1.0])
            x, y, z = float(origin[0]), float(origin[1]), float(origin[2])
            
            pha_lines.append(f"// Spiral Segment Box")
            pha_lines.append(f"{{[ Box: x={x:.4f}; y={y:.4f}; z={z:.4f}; dx={dx}; dy={dy}; dz={dz};]; formula = H20; rho = {default_material.upper()}; priority = 1;}}")
            continue

    return pha_lines

def scad_to_pha(scad_filename, pha_filename, material, phantom_name):
    if not os.path.exists(scad_filename):
        raise FileNotFoundError(f"Input file not found: {scad_filename}")

    with tempfile.NamedTemporaryFile(suffix=".csg", delete=False) as tmp:
        tmp_csg_path = tmp.name

    try:
        print(f"Compiling {scad_filename} to CSG using OpenSCAD...")
        cmd = ["openscad", "-o", tmp_csg_path, scad_filename]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"OpenSCAD compilation failed:\n{result.stderr}")
            return

        with open(tmp_csg_path, "r") as f:
            csg_content = f.read()

        print("Parsing CSG geometries and unfolding spiral matrices...")
        primitive_lines = parse_csg_to_pha(csg_content, material)

        pha_lines = []
        pha_lines.append(f'Phantom "{phantom_name}"\n')
        pha_lines.append(f"// CONRAD Primitive Phantom generated from OpenSCAD: {os.path.basename(scad_filename)}\n")
        pha_lines.extend(primitive_lines)

        with open(pha_filename, "w") as f:
            f.write("\n".join(pha_lines))
            
        print(f"Successfully generated primitive CONRAD phantom: {pha_filename}")

    finally:
        if os.path.exists(tmp_csg_path):
            os.remove(tmp_csg_path)

if __name__ == "__main__":
    args = parse_arguments()
    scad_to_pha(args.input, args.output, args.material, args.phantom_name)