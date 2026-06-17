# Debug script for file writing/reading
import struct
import tempfile
import os

# Create test data
data = bytearray(b'\x00' * 128)
data[40:42] = struct.pack('<H', 16)  # width
print('After setting width:', data[40:42])

# Write to file
with tempfile.NamedTemporaryFile(suffix='.2DB', delete=False) as f:
    f.write(data)
    filepath = f.name

# Read back
with open(filepath, 'rb') as f:
    read_data = f.read()

print('After reading from file:', read_data[40:42])

# Clean up
os.unlink(filepath)

# Now test the actual texture parser
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from io_scene_tdu2.parser import TDU2TextureParser

# Create test data
data = bytearray(b'\x00' * 128)
data[40:42] = struct.pack('<H', 16)  # width
data[42:44] = struct.pack('<H', 16)  # height
data[48:52] = struct.pack('<I', 136)  # param7 (DXT5)

# Write to file
with tempfile.NamedTemporaryFile(suffix='.2DB', delete=False) as f:
    f.write(data)
    filepath = f.name

# Parse the file
print(f'\nParsing texture file: {filepath}')
texture = TDU2TextureParser.parse(filepath)
print(f'Width: {texture.width}, Height: {texture.height}, Format: {texture.Format}')

# Clean up
os.unlink(filepath)
