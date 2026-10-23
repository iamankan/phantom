# Making a digital Phantom
I am making a digital phantom.
Packages:
    - numpy
    - trimesh
    - pyvista
    - matplotlib

To generate a papyrus phantom:
```shell
python3 types/papyrus_scroll_with_ink_grids.py --turns 1 --sheet-thickness-px 1
```
![Phantom](./media/phantom.jpg)

To view that phantom:
```shell
python3 view_phantom.py --input papyrus_phantom
```
![Phantom Viewer](./media/phantom_viewer.jpg)

Phantom Studio Pro:
GUI:
![Phantom Studio Pro](./media/phantom_studio_pro.png)

Output View:
![Phantom Studio Pro Output](./media/app_output.png)


