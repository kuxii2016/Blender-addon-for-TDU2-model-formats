import bpy
import os
import traceback
from bpy_extras.io_utils import ImportHelper, ExportHelper
from .types import (
    TDU2Model, TDU2Mesh, TDUMaterial, TDUTexture2DB, TDUMaterial2DM,
    TDU2ObjectType, TDU2TexFormat, MatFileData
)
from .parser import TDU2ModelParser, TDU2TextureParser, TDU2MaterialParser, TDU2ModelWriter, StringDemangler
from .dds import decode_2db_texture
from mathutils import Vector


class TDU2ImportOperator(bpy.types.Operator, ImportHelper):
    """Import TDU2 model files (.3DG/.3DD)"""
    bl_idname = "import_scene.tdu2_model"
    bl_label = "Import TDU2 Model"
    bl_options = {'PRESET', 'UNDO'}

    filename_ext = ".3DG"
    filter_glob = bpy.props.StringProperty(
        default="*.3DG;*.3DD",
        options={'HIDE'}
    )

    def execute(self, context):
        filepath = self.filepath

        try:
            model = TDU2ModelParser.parse(filepath)
            dirname = os.path.dirname(filepath)
            basename = os.path.splitext(os.path.basename(filepath))[0]

            mat_data_list = None
            dm_path = os.path.join(dirname, basename + ".2dm")
            if os.path.exists(dm_path):
                mat_data_list = TDU2MaterialParser.parse_to_materials(dm_path)
                print(f"[TDU2] Loaded {len(mat_data_list)} materials from .2dm")
                for i, md in enumerate(mat_data_list):
                    print(f"[TDU2]   Material {i}: name='{md.name}' layers={[(l.type_name, l.texture_name) for l in md.texture_layers]}")

            tex_cache = {}
            if os.path.isdir(dirname):
                for fname in os.listdir(dirname):
                    if fname.lower().endswith('.2db'):
                        try:
                            tex = TDU2TextureParser.parse(os.path.join(dirname, fname))
                            key = tex.name
                            tex_cache[key] = (tex, fname)
                            print(f"[TDU2] Cached texture: {fname} key={key} w={tex.width} h={tex.height} fmt={tex.param7}")
                        except Exception as e:
                            print(f"[TDU2] Failed to parse .2db {fname}: {e}")

            self.create_blender_objects(model, mat_data_list, tex_cache)
            self.report({'INFO'}, f"Imported TDU2 model from {filepath}")
            return {'FINISHED'}
        except Exception as e:
            traceback.print_exc()
            self.report({'ERROR'}, f"Failed to import TDU2 model: {str(e)}")
            return {'CANCELLED'}

    def create_blender_objects(self, model, mat_data_list=None, tex_cache=None):
        if tex_cache is None:
            tex_cache = {}
        self._mat_order = []

        if mat_data_list:
            for i, md in enumerate(mat_data_list):
                try:
                    mat = self.create_material_from_matfile(i, md, tex_cache)
                    self._mat_order.append(mat.name if mat else f"material_{i}")
                except Exception as e:
                    print(f"[TDU2] Error creating material {i} ({md.name}): {e}")
                    traceback.print_exc()
                    fallback_name = f"material_{i}"
                    if fallback_name not in bpy.data.materials:
                        fallback_mat = bpy.data.materials.new(name=fallback_name)
                        fallback_mat.use_nodes = True
                    self._mat_order.append(fallback_name)
        else:
            for i, material in enumerate(model.materials):
                mat = self.create_material(i, material)
                self._mat_order.append(mat.name if mat else f"material_{i}")

        print(f"[TDU2] _mat_order ({len(self._mat_order)}): {self._mat_order}")

        # Build group_name -> material_index mapping from .2db filenames
        # Each material's DETAIL/MATERIAL layer references a .2db by internal name
        # The .2db filename suffix (after vehicle prefix) gives the mesh group name
        group_to_mat = {}
        prefix_to_mat = {}
        if mat_data_list and tex_cache:
            for mat_idx, md in enumerate(mat_data_list):
                for layer in md.texture_layers:
                    if layer.type_name in ('DETAIL', 'MATERIAL', 'DETAIL2'):
                        tex_key = layer.texture_name.rstrip(b'\x00')
                        if not tex_key:
                            continue
                        if tex_key not in tex_cache:
                            demangled = StringDemangler.demangle_and_unknown(tex_key)
                            demangled_key = demangled.encode('ascii', errors='replace')
                            if demangled_key in tex_cache:
                                tex_key = demangled_key
                        if tex_key in tex_cache:
                            _, fname = tex_cache[tex_key]
                            base = os.path.splitext(fname)[0]
                            parts = base.split('_', 1)
                            if len(parts) > 1:
                                group = parts[1].upper()
                                if group not in group_to_mat:
                                    group_to_mat[group] = mat_idx
                                    print(f"[TDU2] Material map: suffix='{group}' -> mat_idx={mat_idx} ('{md.name}')")
                            break
            # Build prefix map for fallback matching (e.g., "GLASS" -> "GLASS_F", "GLASS_R")
            for g, mi in group_to_mat.items():
                prefix = g.split('_')[0]
                if prefix not in prefix_to_mat:
                    prefix_to_mat[prefix] = mi
            print(f"[TDU2] Group material map ({len(group_to_mat)}): {group_to_mat}")
            print(f"[TDU2] Prefix material map ({len(prefix_to_mat)}): {prefix_to_mat}")

        # Also try matching group names against material hash/display names
        if mat_data_list:
            for mesh_data in model.meshes:
                g = mesh_data.group_name
                if g in group_to_mat:
                    continue
                for mat_idx, md in enumerate(mat_data_list):
                    # Try hash name match (raw 8 bytes decoded as ASCII)
                    try:
                        hash_str = md.hash_name.rstrip(b'\x00').decode('ascii')
                        if hash_str.upper() == g:
                            group_to_mat[g] = mat_idx
                            prefix_to_mat.setdefault(g.split('_')[0], mat_idx)
                            print(f"[TDU2] Material map (hash): group='{g}' -> mat_idx={mat_idx} ('{md.name}')")
                            break
                    except UnicodeDecodeError:
                        pass
                    # Try display name match
                    if md.name.upper() == g:
                        group_to_mat[g] = mat_idx
                        prefix_to_mat.setdefault(g.split('_')[0], mat_idx)
                        print(f"[TDU2] Material map (name): group='{g}' -> mat_idx={mat_idx} ('{md.name}')")
                        break
            # Known semantic mappings: group keyword -> expected material name
            known_map = {
                'MIRROR': 'Mirror',
                'PLATE': 'Plate_LR',
                'WND': 'Glass',
                'DOOR': 'Paint_LR',
                'BRAKE': 'Break_Parts',
                'BREAK': 'Break_Parts',
                'EXHAUST': 'Chrome',
                'UMP': 'Paint_LR',
                'INT': 'Details',
                'STEER': 'Black',
                'STIR': 'Black',
                'EAT': 'Details',
                'GT_MR': 'Chrome',
                'SPRG': 'Black',
                'RV': 'Mirror',
                'WHEEL': '370Z_Disk',
                'D_SBOX': 'ShadowBox',
                'EADLI': 'headlight',
                'EVERS': 'reversing',
            }
            # Build name -> index lookup
            name_to_idx = {md.name.upper(): mat_idx for mat_idx, md in enumerate(mat_data_list)}
            for mesh_data in model.meshes:
                g = mesh_data.group_name
                if g in group_to_mat:
                    continue
                # A_* groups (wheel arches) -> 370Z_Disk
                if g.startswith('A_') and len(g) > 2:
                    disk_name = '370Z_DISK'
                    if disk_name in name_to_idx:
                        mi = name_to_idx[disk_name]
                        group_to_mat[g] = mi
                        prefix_to_mat.setdefault(g.split('_')[0], mi)
                        print(f"[TDU2] Material map (arch): group='{g}' -> mat_idx={mi} ('370Z_Disk')")
                        continue
                for kw, mat_name in known_map.items():
                    if kw in g:
                        mat_upper = mat_name.upper()
                        if mat_upper in name_to_idx:
                            mi = name_to_idx[mat_upper]
                            group_to_mat[g] = mi
                            prefix_to_mat.setdefault(g.split('_')[0], mi)
                            print(f"[TDU2] Material map (known): group='{g}' -> mat_idx={mi} ('{mat_name}')")
                            break

        for mesh_data in model.meshes:
            # Determine correct material index by group name
            g = mesh_data.group_name
            mi = group_to_mat.get(g)
            if mi is None:
                prefix = g.split('_')[0]
                mi = prefix_to_mat.get(prefix)
            if mi is None:
                mi = mesh_data.material_index
            if mi != mesh_data.material_index:
                print(f"[TDU2] Overriding mat_idx for '{mesh_data.name}': {mesh_data.material_index} -> {mi} (group='{g}')")
                mesh_data.material_index = mi
            print(f"[TDU2] Creating mesh '{mesh_data.name}' mat_idx={mesh_data.material_index} group='{mesh_data.group_name}' verts={len(mesh_data.positions)//3} tris={len(mesh_data.triangles)//3} uvs={len(mesh_data.uvs)//2}")
            self.create_mesh(mesh_data)

    def create_material(self, index, material):
        mat_name = f"material_{index}"
        if mat_name in bpy.data.materials:
            return bpy.data.materials[mat_name]

        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
        mat.diffuse_color = (material.diffuse[0], material.diffuse[1], material.diffuse[2], material.diffuse[3])
        mat.specular_color = (material.specular[0], material.specular[1], material.specular[2])

        if material.diffuse_texture_bytes:
            self._apply_tex_to_mat(mat, material.diffuse_texture_bytes, material.diffuse_texture_width, material.diffuse_texture_height, f"texture_{index}")

        return mat

    def create_material_from_matfile(self, index, md, tex_cache):
        print(f"[TDU2] Creating material {index}: {md.name} ({len(md.texture_layers)} layers)")
        mat_name = md.name if md.name else f"material_{index}"
        if mat_name in bpy.data.materials:
            return bpy.data.materials[mat_name]

        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
        mat.diffuse_color = (md.diffuse[0], md.diffuse[1], md.diffuse[2], md.diffuse[3])
        mat.specular_color = (md.specular[0], md.specular[1], md.specular[2])

        for layer in md.texture_layers:
            tex_key = layer.texture_name.rstrip(b'\x00')
            if not tex_key:
                continue
            if tex_key not in tex_cache:
                demangled = StringDemangler.demangle_and_unknown(tex_key)
                demangled_key = demangled.encode('ascii', errors='replace')
                if demangled_key in tex_cache:
                    tex_key = demangled_key
            if tex_key in tex_cache:
                tex2db, tex_fname = tex_cache[tex_key]
                try:
                    rgba = decode_2db_texture(tex2db)
                    display_name = os.path.splitext(tex_fname)[0]
                    self._apply_tex_to_mat(mat, rgba, tex2db.width, tex2db.height, display_name)
                except Exception as e:
                    print(f"[TDU2] Failed to decode texture '{tex_key}' ({tex_fname}): {e}")
            else:
                print(f"[TDU2] Texture key '{tex_key}' not found in cache.")

        return mat

    def _apply_tex_to_mat(self, mat, rgba_bytes, width, height, tex_name):
        print(f"[TDU2] Applying texture: {tex_name} w={width} h={height} len={len(rgba_bytes)}")
        if tex_name in bpy.data.images:
            img = bpy.data.images[tex_name]
        else:
            img = bpy.data.images.new(name=tex_name, width=width, height=height, alpha=True)
            pixels = []
            for i in range(0, len(rgba_bytes), 4):
                pixels.append(rgba_bytes[i + 2] / 255.0)
                pixels.append(rgba_bytes[i + 1] / 255.0)
                pixels.append(rgba_bytes[i] / 255.0)
                pixels.append(rgba_bytes[i + 3] / 255.0)
            img.pixels = pixels

        tex_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
        tex_node.image = img

        bsdf = mat.node_tree.nodes.get('Principled BSDF')
        if bsdf:
            mat.node_tree.links.new(tex_node.outputs['Color'], bsdf.inputs['Base Color'])
            mat.node_tree.links.new(tex_node.outputs['Alpha'], bsdf.inputs['Alpha'])

    @staticmethod
    def _yup_to_zup(v):
        return Vector((v[0], v[2], v[1]))

    def create_mesh(self, mesh_data):
        mesh = bpy.data.meshes.new(name=mesh_data.name)

        raw_verts = [Vector(mesh_data.positions[i:i+3]) for i in range(0, len(mesh_data.positions), 3)]
        verts = [self._yup_to_zup(v) for v in raw_verts]
        faces = [mesh_data.triangles[i:i+3] for i in range(0, len(mesh_data.triangles), 3)]
        mesh.from_pydata(verts, [], faces)
        mesh.update()

        if mesh_data.normals:
            raw_normals = [Vector(mesh_data.normals[i:i+3]) for i in range(0, len(mesh_data.normals), 3)]
            v_normals = [self._yup_to_zup(n) for n in raw_normals]
            loop_normals = []
            for loop in mesh.loops:
                vi = loop.vertex_index
                loop_normals.append(v_normals[vi] if vi < len(v_normals) else Vector((0, 0, 1)))
            mesh.use_auto_smooth = True
            mesh.normals_split_custom_set(loop_normals)

        if mesh_data.uvs:
            uv_pairs = [(mesh_data.uvs[i], mesh_data.uvs[i+1]) for i in range(0, len(mesh_data.uvs), 2)]
            uv_layer = mesh.uv_layers.new(name="UVMap")
            for loop in mesh.loops:
                vi = loop.vertex_index
                if vi < len(uv_pairs):
                    uv_layer.data[loop.index].uv = uv_pairs[vi]

        obj = bpy.data.objects.new(mesh_data.name, mesh)

        mi = mesh_data.material_index
        if 0 <= mi < len(self._mat_order):
            mat_name = self._mat_order[mi]
            if mat_name in bpy.data.materials:
                obj.data.materials.append(bpy.data.materials[mat_name])
                print(f"[TDU2]   -> assigned material '{mat_name}' to mesh '{mesh_data.name}'")
            else:
                print(f"[TDU2]   -> WARNING: material '{mat_name}' (idx {mi}) not found in bpy.data.materials")

        bpy.context.collection.objects.link(obj)
        return obj


class TDU2ExportOperator(bpy.types.Operator, ExportHelper):
    """Export TDU2 model files (.3DG/.3DD)"""
    bl_idname = "export_scene.tdu2_model"
    bl_label = "Export TDU2 Model"
    bl_options = {'PRESET'}

    filename_ext = ".3DG"
    filter_glob = bpy.props.StringProperty(
        default="*.3DG",
        options={'HIDE'}
    )

    def execute(self, context):
        filepath = self.filepath
        
        try:
            # Convert selected objects to TDU2 format
            model = self.convert_to_tdu2_model()
            
            # Write the model
            TDU2ModelWriter.write(filepath, model)
            
            self.report({'INFO'}, f"Exported TDU2 model to {filepath}")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to export TDU2 model: {str(e)}")
            return {'CANCELLED'}

    def convert_to_tdu2_model(self):
        model = TDU2Model()
        
        # Collect materials from selected objects
        materials = []
        for obj in bpy.context.selected_objects:
            if obj.data.materials:
                for mat in obj.data.materials:
                    tdu_mat = TDUMaterial()
                    tdu_mat.name = mat.name
                    if mat.node_tree:
                        self.extract_material_from_nodes(tdu_mat, mat)
                    materials.append(tdu_mat)
        
        model.materials = materials
        
        # Collect meshes from selected objects
        meshes = []
        for obj in bpy.context.selected_objects:
            if obj.type == 'MESH':
                tdu_mesh = self.convert_blender_mesh_to_tdu2(obj)
                meshes.append(tdu_mesh)
        
        model.meshes = meshes
        
        return model

    def extract_material_from_nodes(self, material, blender_mat):
        if not blender_mat.node_tree:
            return
        
        # Try to extract from Principled BSDF
        for node in blender_mat.node_tree.nodes:
            if node.type == 'Principled BSDF':
                material.diffuse = [node.inputs['Base Color'].default_value] * 4
                material.ambient = [0.2] * 4
                material.specular = [node.inputs['Specular'].default_value] * 4
                
                # Try to find texture node
                for link in blender_mat.node_tree.links:
                    if link.to_node == node and link.from_node.type == 'TexImage':
                        material.diffuse_texture_bytes = link.from_node.image.pixels[:]
                        material.diffuse_texture_width = link.from_node.image.size[0]
                        material.diffuse_texture_height = link.from_node.image.size[1]
                        break
                break

    @staticmethod
    def _zup_to_yup(v):
        return (v[0], v[2], v[1])

    def convert_blender_mesh_to_tdu2(self, obj):
        mesh_data = TDU2Mesh()
        mesh_data.name = obj.name
        
        # Convert vertices (Z-up to Y-up)
        mesh_data.positions = []
        for vertex in obj.data.vertices:
            mesh_data.positions.extend(self._zup_to_yup(vertex.co))
        
        # Convert normals (Z-up to Y-up)
        if obj.data.normals:
            mesh_data.normals = []
            for vertex in obj.data.vertices:
                mesh_data.normals.extend(self._zup_to_yup(vertex.normal))
        
        # Convert UVs
        if obj.data.uv_layers:
            uv_layer = obj.data.uv_layers[0]
            mesh_data.uvs = [uv for vertex in uv_layer.data for uv in vertex.uv]
        
        # Convert triangles
        mesh_data.triangles = []
        for poly in obj.data.polygons:
            indices = poly.vertices
            if len(indices) >= 3:
                mesh_data.triangles.extend([indices[0], indices[1], indices[2]])
        
        # Find material index
        if obj.data.materials and obj.active_material:
            for i, mat in enumerate(bpy.data.materials):
                if mat == obj.active_material:
                    mesh_data.material_index = i
                    mesh_data.material_name = mat.name
                    break
        
        return mesh_data


class TDU2ImportTextureOperator(bpy.types.Operator, ImportHelper):
    """Import TDU2 texture files (.2DB)"""
    bl_idname = "import_scene.tdu2_texture"
    bl_label = "Import TDU2 Texture"
    bl_options = {'PRESET'}

    filename_ext = ".2DB"
    filter_glob = bpy.props.StringProperty(
        default="*.2DB",
        options={'HIDE'}
    )

    def execute(self, context):
        filepath = self.filepath
        
        try:
            texture = TDU2TextureParser.parse(filepath)
            self.create_blender_texture(texture)
            self.report({'INFO'}, f"Imported TDU2 texture from {filepath}")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to import TDU2 texture: {str(e)}")
            return {'CANCELLED'}

    def create_blender_texture(self, texture):
        tex_name = f"texture_{texture.name}"
        if tex_name in bpy.data.images:
            return bpy.data.images[tex_name]

        rgba = decode_2db_texture(texture)
        tex_image = bpy.data.images.new(name=tex_name, width=texture.width,
                                        height=texture.height, alpha=True)
        pixels = []
        for i in range(0, len(rgba), 4):
            pixels.append(rgba[i + 2] / 255.0)
            pixels.append(rgba[i + 1] / 255.0)
            pixels.append(rgba[i] / 255.0)
            pixels.append(rgba[i + 3] / 255.0)
        tex_image.pixels = pixels

        return tex_image


class TDU2ImportMaterialOperator(bpy.types.Operator, ImportHelper):
    """Import TDU2 material files (.2DM)"""
    bl_idname = "import_scene.tdu2_material"
    bl_label = "Import TDU2 Material"
    bl_options = {'PRESET'}

    filename_ext = ".2DM"
    filter_glob = bpy.props.StringProperty(
        default="*.2DM",
        options={'HIDE'}
    )

    def execute(self, context):
        filepath = self.filepath
        
        try:
            material2d = TDU2MaterialParser.parse(filepath)
            self.create_blender_materials(material2d)
            self.report({'INFO'}, f"Imported TDU2 materials from {filepath}")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to import TDU2 materials: {str(e)}")
            return {'CANCELLED'}

    def create_blender_materials(self, material2d):
        for seg in material2d.segments:
            if seg.__class__.__name__ == 'MatFileSegment':
                mat_name = seg.Name if seg.Name else f"material_{seg.HashName}"
                if mat_name in bpy.data.materials:
                    continue
                
                mat = bpy.data.materials.new(name=mat_name)
                mat.use_nodes = True
                mat.diffuse_color = (seg.Diffuse.R, seg.Diffuse.G, seg.Diffuse.B, seg.Diffuse.A)
                mat.specular_color = (seg.Specular.R, seg.Specular.G, seg.Specular.B)
                
                # TODO: Import texture layers
                # for i in range(seg.NbOfLayers):
                #     tex_name = seg.GetTextureLayerTexture(i)
                #     if tex_name:
                #         self.create_texture_from_name(tex_name, mat, i)


# Register the operators
classes = [
    TDU2ImportOperator,
    TDU2ExportOperator,
    TDU2ImportTextureOperator,
    TDU2ImportMaterialOperator,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.TOPBAR_MT_file_import.append(tdu2_import_menu_func)
    bpy.types.TOPBAR_MT_file_export.append(tdu2_export_menu_func)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(tdu2_import_menu_func)
    bpy.types.TOPBAR_MT_file_export.remove(tdu2_export_menu_func)
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


def tdu2_import_menu_func(self, context):
    self.layout.operator(TDU2ImportOperator.bl_idname, icon='IMPORT')
    self.layout.operator(TDU2ImportTextureOperator.bl_idname, icon='TEXTURE')
    self.layout.operator(TDU2ImportMaterialOperator.bl_idname, icon='MATERIAL')


def tdu2_export_menu_func(self, context):
    self.layout.operator(TDU2ExportOperator.bl_idname, icon='EXPORT')


if __name__ == "__main__":
    register()