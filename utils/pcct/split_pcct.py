import argparse
import numpy as np
import tifffile

def main():
    parser = argparse.ArgumentParser(description="Split a 4D PCCT TIFF file into separate energy bin files.")
    parser.add_argument("-i", "--input-path", type=str, help="Path to the input multi-bin .tif file")
    parser.add_argument("-o", "--output-prefix", type=str, default="energy_bin", help="Prefix for output files")
    args = parser.parse_args()

    print(f"Reading input file: {args.input_path}")
    data = tifffile.imread(args.input_path)
    print(f"Loaded array shape: {data.shape} (Expected: TZYX)")

    # Ensure it has the expected 4D shape (bins, slices, height, width)
    if data.ndim == 4:
        num_bins = data.shape[0]
        for i in range(num_bins):
            bin_data = data[i] # Shape: (200, 256, 256) -> ZYX format
            output_filename = f"{args.output_prefix}_{i+1}.tif"
            tifffile.imwrite(output_filename, bin_data)
            print(f"Saved Energy Bin {i+1} to {output_filename} with shape {bin_data.shape}")
    else:
        print(f"Error: Unexpected array dimensions {data.ndim}. Expected 4D array.")

if __name__ == "__main__":
    main()