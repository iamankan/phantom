import argparse
import os

def parse_arguments():
    parser = argparse.ArgumentParser(description="Generate CONRAD .pha flat board with horizontal material bars read from a text file.")
    parser.add_argument("-o", "--output", required=True, help="Path to the output .pha phantom file")
    parser.add_argument("-b", "--base-material", default="PAPYRUS", help="Base substrate material (default: PAPYRUS)")
    parser.add_argument("-m", "--material-file", required=True, help="Path to text file containing material names line-by-line")
    parser.add_argument("--hwd", type=float, nargs=3, default=[0.15, 10.0, 10.0], 
                        help="Three dimensions for substrate board (Height, Width, Depth in cm). Min -> depth (dy), Mid -> width (dx), Max -> height (dz).")
    parser.add_argument("--ink-thick", type=float, default=0.05, help="Thickness of material strips in cm (dy)")
    parser.add_argument("--phantom-name", default="Horizontal_Bars_Phantom", help="Name of the phantom")
    return parser.parse_args()

def load_materials_from_file(filepath):
    """Reads materials line-by-line, stripping comments and whitespace."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Material file not found: {filepath}")
    
    materials = []
    with open(filepath, "r") as f:
        for line in f:
            cleaned = line.strip()
            if cleaned and not cleaned.startswith("#"):
                materials.append(cleaned.upper())
                
    if not materials:
        raise ValueError(f"No valid materials found in {filepath}")
    return materials

def generate_horizontal_bars(pha_filename, base_material, material_file, hwd_vals, ink_thick, phantom_name):
    # Load materials sequence from file
    materials = load_materials_from_file(material_file)
    num_bars = len(materials)
    print(f"Loaded {num_bars} materials from {material_file}: {materials}")

    # Sort HWD: min = depth/thickness (dy), mid = width (dx), max = height (dz)
    sorted_dims = sorted(hwd_vals)
    board_depth = sorted_dims[0]   # Min -> dy (thickness)
    board_width = sorted_dims[1]   # Mid -> dx (width)
    board_height = sorted_dims[2]  # Max -> dz (height)

    pha_lines = []
    pha_lines.append(f'Phantom "{phantom_name}"\n')
    pha_lines.append(f"// Flat Board Horizontal Bars Phantom using file: {material_file}\n")
    pha_lines.append(f"// Base Material: {base_material.upper()} | Board [Width(dx): {board_width}, Depth(dy): {board_depth}, Height(dz): {board_height}] (cm)\n")
    
    # 1. Base Board Box (Continuous substrate)
    pha_lines.append(f"// --- Base Substrate Board ---")
    pha_lines.append(
        f"{{[ Box: x=0.0; y=0.0; z=0.0; "
        f"dx={board_width}; dy={board_depth}; dz={board_height};]; "
        f"formula = H20; rho = {base_material.upper()}; priority = 1;}}"
    )
    
    # 2. Horizontal Bar Heights (Total height divided evenly by number of materials)
    bar_height = board_height / num_bars
    
    # Position material strips on the front face of the board
    strip_y = (board_depth / 2.0) + (ink_thick / 2.0)
    
    pha_lines.append(f"// --- Horizontal Material Strips (Top to Bottom) ---")
    for i, mat in enumerate(materials):
        if mat not in ["NONE", "EMPTY", "BG"]:
            # Calculate Z center for this bar, starting from the top (+height/2) down to the bottom (-height/2)
            bar_z = (board_height / 2.0) - (i * bar_height) - (bar_height / 2.0)
            
            pha_lines.append(
                f"{{[ Box: x=0.0; y={strip_y:.4f}; z={bar_z:.4f}; "
                f"dx={board_width:.4f}; dy={ink_thick}; dz={bar_height:.4f};]; "
                f"formula = H20; rho = {mat}; priority = 2;}}"
            )

    with open(pha_filename, "w") as f:
        f.write("\n".join(pha_lines))
        
    print(f"Successfully generated horizontal bars phantom: {pha_filename}")

if __name__ == "__main__":
    args = parse_arguments()
    generate_horizontal_bars(
        args.output, 
        args.base_material, 
        args.material_file,
        args.hwd, 
        args.ink_thick, 
        args.phantom_name
    )