import argparse
import tifffile

def main():
    parser = argparse.ArgumentParser(description="Read a TIFF file and inspect its dimensions.")
    parser.add_argument("-i", "--input-path", type=str, help="Path to the input .tif file")
    args = parser.parse_args()

    try:
        # Open the TIFF file and inspect shape/metadata
        with tifffile.TiffFile(args.input_path) as tif:
            print(f"\n--- File Info: {args.input_path} ---")
            data = tif.asarray()
            print(f"Array Shape (Dimensions): {data.shape}")
            print(f"Data Type               : {data.dtype}")
            print(f"Number of Pages/Slices  : {len(tif.pages)}")
            
            if hasattr(tif, 'series') and len(tif.series) > 0:
                print(f"Series Shape            : {tif.series[0].shape}")
                print(f"Axes                    : {tif.series[0].axes}")
                
    except Exception as e:
        print(f"Error reading TIFF file: {e}")

if __name__ == "__main__":
    main()