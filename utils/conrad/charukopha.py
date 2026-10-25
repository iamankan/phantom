import argparse

def parse_arguments():
    parser = argparse.ArgumentParser(description="Generate CONRAD .pha flat board charuko phantom with background-separated inks.")
    parser.add_argument("-o", "--output", required=True, help="Path to the output .pha phantom file")
    parser.add_argument("-b", "--base-material", default="PAPYRUS", help="Base substrate material (default: PAPYRUS)")
    parser.add_argument("--hwd", type=float, nargs=3, default=[0.15, 10.0, 10.0], 
                        help="Three dimensions for substrate board (Height, Width, Depth in cm). Min -> depth (dy), Mid -> width (dx), Max -> height (dz).")
    parser.add_argument("--cols", type=int, default=8, help="Number of equal columns along width (dx)")
    parser.add_argument("--rows", type=int, default=8, help="Number of equal rows along height (dz)")
    parser.add_argument("--ink-thick", type=float, default=0.05, help="Thickness of ink patches in cm (dy)")
    parser.add_argument("--phantom-name", default="Flat_Board_Charuko_Phantom", help="Name of the phantom")
    return parser.parse_args()

def generate_flat_board_phantom(pha_filename, base_material, hwd_vals, cols, rows, ink_thick, phantom_name):
    # Sort HWD: min = depth/thickness (dy), mid = width (dx), max = height (dz)
    sorted_dims = sorted(hwd_vals)
    board_depth = sorted_dims[0]   # Min -> dy (thickness)
    board_width = sorted_dims[1]   # Mid -> dx (width)
    board_height = sorted_dims[2]  # Max -> dz (height)

    pha_lines = []
    pha_lines.append(f'Phantom "{phantom_name}"\n')
    pha_lines.append(f"// Flat Board Charuko Phantom with Background-Separated Inks\n")
    pha_lines.append(f"// Base Material: {base_material.upper()} | Board [Width(dx): {board_width}, Depth(dy): {board_depth}, Height(dz): {board_height}] (cm)\n")
    
    # 1. Base Board Box (Continuous substrate)
    pha_lines.append(f"// --- Base Substrate Board ---")
    pha_lines.append(
        f"{{[ Box: x=0.0; y=0.0; z=0.0; "
        f"dx={board_width}; dy={board_depth}; dz={board_height};]; "
        f"formula = H20; rho = {base_material.upper()}; priority = 1;}}"
    )
    
    # 2. Uniform & Equidistant Grid Divisions
    cell_width = board_width / cols
    cell_height = board_height / rows
    
    # Position ink patches on the front face of the board
    ink_y = (board_depth / 2.0) + (ink_thick / 2.0)
    
    pha_lines.append(f"// --- Isolated Ink Patches Separated by Background Substrate ---")
    for r in range(rows):
        row_z = (r * cell_height) - (board_height / 2.0) + (cell_height / 2.0)
        
        for c in range(cols):
            # If (r + c) is even, place an alternating ink. If odd, leave NONE (background).
            if (r + c) % 2 == 0:
                selected_ink = "IRONGALLINK" if ((r + c) // 2) % 2 == 0 else "LAMPBLACKINK"
                
                col_x = (c * cell_width) - (board_width / 2.0) + (cell_width / 2.0)
                
                pha_lines.append(
                    f"{{[ Box: x={col_x:.4f}; y={ink_y:.4f}; z={row_z:.4f}; "
                    f"dx={cell_width:.4f}; dy={ink_thick}; dz={cell_height:.4f};]; "
                    f"formula = H20; rho = {selected_ink}; priority = 2;}}"
                )

    with open(pha_filename, "w") as f:
        f.write("\n".join(pha_lines))
        
    print(f"Successfully generated background-separated charuko phantom: {pha_filename}")

if __name__ == "__main__":
    args = parse_arguments()
    generate_flat_board_phantom(
        args.output, 
        args.base_material, 
        args.hwd, 
        args.cols, 
        args.rows, 
        args.ink_thick, 
        args.phantom_name
    )