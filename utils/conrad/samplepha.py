import argparse
import math

def parse_arguments():
    parser = argparse.ArgumentParser(description="Generate CONRAD .pha spiral phantom with outward-facing Ellipt_Cyl.")
    parser.add_argument("-o", "--output", required=True, help="Path to the output .pha phantom file")
    parser.add_argument("-n", "--segments", type=int, default=60, help="Number of spiral segments (default: 60)")
    parser.add_argument("--phantom-name", default="Outward_Elliptic_Cyl_Scroll", help="Name of the phantom")
    return parser.parse_args()

def generate_outward_ellipt_cyl(pha_filename, total_segments, phantom_name):
    # Scroll Parameters
    initial_radius = 2.0     
    page_len = 0.8           # Thickness / span of the segment
    page_thick = 0.15        # Width of the scroll layer
    page_height = 50.0       # Length (l) along Z-axis
    
    ink_len = 0.5            
    ink_thick = 0.05         
    ink_height = 40.0        
    
    ink_pattern = ["lampblack", "irongall", "none"]
    
    pha_lines = []
    pha_lines.append(f'Phantom "{phantom_name}"\n')
    pha_lines.append(f"// Open Spiral Scroll with Outward-Facing Ellipt_Cyl Primitives\n")
    
    current_angle = 0.0
    radius = initial_radius
    
    for i in range(total_segments):
        x = radius * math.cos(current_angle)
        y = radius * math.sin(current_angle)
        z = 0.0  
        
        # Tangent angle vs Normal (Outward) angle
        # Adding 90 degrees (pi/2) rotates the cross-section orientation to face outward
        normal_angle_deg = math.degrees(current_angle) + 90.0
        
        # 1. Papyrus Elliptical Cylinder Segment (Facing Outward)
        pha_lines.append(f"// Segment {i+1} - Papyrus")
        pha_lines.append(
            f"{{[ Ellipt_Cyl: x={x:.4f}; y={y:.4f}; z={z:.4f}; "
            f"dx={page_len}; dy={page_thick}; l={page_height}; "
            f"axis(0,0,1); a_x(cos({normal_angle_deg:.2f}), sin({normal_angle_deg:.2f}), 0);]; "
            f"formula = H20; rho = PAPYRUS; priority = 1;}}"
        )
        
        # 2. Alternating Ink Layer Segment
        ink_type = ink_pattern[i % len(ink_pattern)]
        if ink_type != "none":
            material_name = "LAMPBLACKINK" if ink_type == "lampblack" else "IRONGALLINK"
            
            ink_radius = radius - page_thick - (ink_thick / 2.0)
            ink_x = ink_radius * math.cos(current_angle)
            ink_y = ink_radius * math.sin(current_angle)
            ink_z = (page_height - ink_height) / 2.0  
            
            pha_lines.append(f"// Segment {i+1} - Ink ({ink_type})")
            pha_lines.append(
                f"{{[ Ellipt_Cyl: x={ink_x:.4f}; y={ink_y:.4f}; z={ink_z:.4f}; "
                f"dx={ink_len}; dy={ink_thick}; l={ink_height}; "
                f"axis(0,0,1); a_x(cos({normal_angle_deg:.2f}), sin({normal_angle_deg:.2f}), 0);]; "
                f"formula = H20; rho = {material_name}; priority = 1;}}"
            )
        
        # Step forward along the spiral curve
        d_theta = page_len / radius
        current_angle += d_theta
        radius += (page_thick * 2.0 + ink_thick * 2.0 + 0.1) / (2.0 * math.pi)

    with open(pha_filename, "w") as f:
        f.write("\n".join(pha_lines))
        
    print(f"Successfully generated outward-facing Ellipt_Cyl phantom: {pha_filename}")

if __name__ == "__main__":
    args = parse_arguments()
    generate_outward_ellipt_cyl(args.output, args.segments, args.phantom_name)