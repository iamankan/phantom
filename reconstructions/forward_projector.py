import argparse
import os
import itk
from itk import RTK as rtk
import numpy as np

def run_rtk_projection(mhd_path, output_path, num_angles=360, sod=600.0, sdd=1000.0):
    print("Loading volume with SimpleITK/ITK...")
    if not os.path.exists(mhd_path):
        raise FileNotFoundError(f"Input file not found: {mhd_path}")

    # Read input volume
    PixelType = itk.F
    VolumeType = itk.Image[PixelType, 3]
    reader = itk.ImageFileReader[VolumeType].New(FileName=mhd_path)
    reader.Update()
    volume_image = reader.GetOutput()
    
    # Get metadata for dimensions
    region = volume_image.GetLargestPossibleRegion()
    size = region.GetSize()
    spacing = volume_image.GetSpacing()
    
    nz, ny, nx = size[2], size[1], size[0]
    
    print(f"Volume loaded. Shape (X, Y, Z): {nx}x{ny}x{nz}, Spacing: {spacing}")

    # Set up RTK Constant Image Source for the projection stack (Detector definition)
    ProjectionStackType = itk.Image[PixelType, 3]
    constantImageSource = rtk.ConstantImageSource[ProjectionStackType].New()
    
    # Define detector sizing and spacing
    detector_spacing_x = spacing[0]
    detector_spacing_z = spacing[2]
    
    constantImageSource.SetOrigin([
        - (nx * detector_spacing_x) / 2.0, 
        - (ny * detector_spacing_z) / 2.0, 
        0.0
    ])
    constantImageSource.SetSpacing([detector_spacing_x, detector_spacing_z, 1.0])
    constantImageSource.SetSize([nx, nz, num_angles])  # [DetectorCols, DetectorRows, NumAngles]
    constantImageSource.SetConstant(0.0)

    # Configure RTK Circular Geometry
    geometry = rtk.ThreeDCircularProjectionGeometry.New()
    
    for i in range(num_angles):
        angle_rad = i * (2.0 * 3.141592653589793 / num_angles)
        angle_deg = angle_rad * (180.0 / 3.141592653589793)
        geometry.AddProjection(angle_deg, sod, sdd, 0.0, 0.0, 0.0, 0.0, 0.0)

    # Set up RTK Joseph Forward Projector Filter
    print("Executing RTK Joseph Forward Projector...")
    ImageType3D = itk.Image[itk.F, 3]
    forward_projector = rtk.JosephForwardProjectionImageFilter[ImageType3D, ImageType3D].New()
    forward_projector.SetInput(0, constantImageSource.GetOutput())
    forward_projector.SetInput(1, volume_image)
    forward_projector.SetGeometry(geometry)
    forward_projector.Update()

    # Robust output path handling (ensures a valid file extension and directory structure)
    if os.path.isdir(output_path) or output_path.endswith('/'):
        os.makedirs(output_path, exist_ok=True)
        final_output_path = os.path.join(output_path, "projections.mhd")
    elif not any(output_path.endswith(ext) for ext in ['.mhd', '.raw', '.nrrd', '.nii', '.mha']):
        # If no extension was provided, treat it as a base path and add .mhd
        final_output_path = output_path + ".mhd"
        parent_dir = os.path.dirname(os.path.abspath(final_output_path))
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
    else:
        final_output_path = output_path
        parent_dir = os.path.dirname(os.path.abspath(final_output_path))
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

    # Save output projection stack
    print(f"Saving projection stack to {final_output_path}...")
    writer = itk.ImageFileWriter[ProjectionStackType].New()
    writer.SetFileName(final_output_path)
    writer.SetInput(forward_projector.GetOutput())
    writer.Update()
    
    print(f"RTK projection stack successfully saved to {final_output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run RTK 3D Forward Projector via Python venv.")
    parser.add_argument("-i", "--input", required=True, help="Path to input .mhd file.")
    parser.add_argument("-o", "--output", required=True, help="Path to output .mhd file or base name.")
    parser.add_argument("-n", "--num-angles", type=int, default=360, help="Number of projection angles.")
    parser.add_argument("--sod", type=float, default=600.0, help="Source-to-Object Distance (mm).")
    parser.add_argument("--sdd", type=float, default=1000.0, help="Source-to-Detector Distance (mm).")
    
    args = parser.parse_args()
    run_rtk_projection(args.input, args.output, args.num_angles, args.sod, args.sdd)