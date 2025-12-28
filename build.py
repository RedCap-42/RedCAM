import PyInstaller.__main__
import os
import shutil

def build():
    # Clean previous builds
    if os.path.exists('build'):
        shutil.rmtree('build')
    if os.path.exists('dist'):
        shutil.rmtree('dist')

    # Define PyInstaller arguments
    args = [
        'main.py',  # Entry point
        '--name=RedCAM',
        '--onefile',  # Create a single executable
        '--windowed',  # No console window
        '--clean',
        '--paths=src',  # Add src to path
        # Add hidden imports if necessary (e.g. for folium or plugins)
        '--hidden-import=folium',
        '--hidden-import=branca',
        '--hidden-import=jinja2',
        '--hidden-import=PyQt6.QtWebEngineWidgets',
        # Collect data files if needed. 
        # For now, we don't have explicit data files like images found, 
        # but if we did, we'd use --add-data "src/path/to/file;dest/path"
    ]

    print("Building RedCAM...")
    PyInstaller.__main__.run(args)
    print("Build complete. Executable is in 'dist' folder.")

if __name__ == "__main__":
    build()
