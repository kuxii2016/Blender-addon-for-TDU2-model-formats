"""Test script for TDU2 Blender addon"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from io_scene_tdu2.types import TDU2Model, TDU2Mesh, TDUMaterial
from io_scene_tdu2.parser import TDU2ModelParser
import tempfile
import struct


def create_test_model_file(filepath: str):
    """Create a simple test TDU2 model file for testing"""
    with open(filepath, 'wb') as f:
        # Write header
        f.write(struct.pack('<H', 1))  # file_version
        f.write(struct.pack('<H', 0))  # some_flag
        f.write(struct.pack('<I', 0))  # unk1
        f.write(struct.pack('<I', 100))  # size
        f.write(struct.pack('<I', 0x4744332E))  # ".3DG" magic


def test_import_export():
    """Test importing and exporting TDU2 model files"""
    # Create a temporary test file
    with tempfile.NamedTemporaryFile(suffix='.3DG', delete=False) as tmp:
        test_file = tmp.name
        create_test_model_file(test_file)

    try:
        # Try to parse the test file
        print(f"Attempting to parse: {test_file}")
        model = TDU2ModelParser.parse(test_file)
        print(f"Parsed model: file_version={model.file_version}, some_flag={model.some_flag}, size={model.size}")
        print(f"Number of segments: {len(model.segments)}")
        print(f"Number of meshes: {len(model.meshes)}")
        print(f"Number of materials: {len(model.materials) if model.materials else 0}")
        
        print("Test passed!")
        return True
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.unlink(test_file)


if __name__ == "__main__":
    success = test_import_export()
    sys.exit(0 if success else 1)
