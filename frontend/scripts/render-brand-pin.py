"""Render with Blender 5: blender --background --python scripts/render-brand-pin.py."""

import math
from pathlib import Path

import bpy
from mathutils import Vector


OUTPUT = Path(__file__).resolve().parents[1] / "public/brand/brand-pin.png"
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)


def material(name, hex_color, roughness=0.42):
    rgb = [int(hex_color[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in rgb]
    mat = bpy.data.materials.new(name)
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*linear, 1)
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = 0.05
    shader.inputs["Specular IOR Level"].default_value = 0.25
    return mat


mint = material("Brand mint", "34C8B0")
green = material("Deep green", "004D46")
pale = material("Pale mint", "A4EBDD")

# Four loops form an extruded pin with an open circular center.
count = 128
outer = []
inner = []
for i in range(count):
    angle = 2 * math.pi * i / count
    sine, cosine = math.sin(angle), math.cos(angle)
    radius = 1.48
    if 5 * math.pi / 4 < angle < 7 * math.pi / 4:
        radius = -2.55 / (sine - 1.437 * abs(cosine))
    outer.append((radius * cosine, 0.5 + radius * sine))
    inner.append((0.91 * cosine, 0.5 + 0.91 * sine))

vertices = [(x, depth, z) for depth in (-0.26, 0.26) for loop in (outer, inner) for x, z in loop]
faces = []
for i in range(count):
    j = (i + 1) % count
    faces.extend([
        (i, j, count + j, count + i),
        (2 * count + j, 2 * count + i, 3 * count + i, 3 * count + j),
        (j, i, 2 * count + i, 2 * count + j),
        (count + i, count + j, 3 * count + j, 3 * count + i),
    ])

mesh = bpy.data.meshes.new("Pin geometry")
mesh.from_pydata(vertices, [], faces)
mesh.update()
pin = bpy.data.objects.new("Localhost Daegu pin", mesh)
bpy.context.collection.objects.link(pin)
pin.data.materials.append(mint)
bpy.context.view_layer.objects.active = pin
pin.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.mode_set(mode="OBJECT")
pin.select_set(False)
bevel = pin.modifiers.new("Soft edges", "BEVEL")
bevel.width = 0.075
bevel.segments = 5
pin.modifiers.new("Weighted normals", "WEIGHTED_NORMAL")


def stroke(name, points):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = 0.095
    curve.bevel_resolution = 5
    curve.use_fill_caps = True
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, (x, z) in zip(spline.points, points):
        point.co = (x, -0.28, z, 1)
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(green)


stroke("Terminal chevron", [(-0.46, 0.9), (-0.09, 0.54), (-0.46, 0.18)])
stroke("Terminal underscore", [(0.13, 0.17), (0.60, 0.17)])

for name, position, size, mat in [
    ("Data block 1", (0.99, -0.32, -1.04), 0.48, pale),
    ("Data block 2", (1.60, -0.25, -1.04), 0.46, mint),
    ("Data block 3", (0.99, -0.29, -1.67), 0.43, mint),
]:
    bpy.ops.mesh.primitive_cube_add(size=size, location=position)
    block = bpy.context.object
    block.name = name
    block.data.materials.append(mat)
    bevel = block.modifiers.new("Rounded corners", "BEVEL")
    bevel.width = 0.09
    bevel.segments = 6
    block.modifiers.new("Weighted normals", "WEIGHTED_NORMAL")


def aim(obj, point):
    obj.rotation_euler = (Vector(point) - obj.location).to_track_quat("-Z", "Y").to_euler()


for name, position, power, size in [
    ("Large softbox", (-4, -5, 7), 750, 5),
    ("Fill", (5, -2, 3), 400, 4),
    ("Rim", (1, 4, 5), 850, 3),
]:
    bpy.ops.object.light_add(type="AREA", location=position)
    lamp = bpy.context.object
    lamp.name = name
    lamp.data.energy = power
    lamp.data.shape = "DISK"
    lamp.data.size = size
    aim(lamp, (0, 0, 0))

bpy.ops.object.camera_add(location=(3.4, -9, 3.3))
camera = bpy.context.object
aim(camera, (0.15, 0, -0.08))
camera.data.type = "ORTHO"
camera.data.ortho_scale = 5.55
scene = bpy.context.scene
scene.camera = camera
scene.render.engine = "CYCLES"
scene.cycles.samples = 128
scene.cycles.use_denoising = True
scene.render.threads_mode = "FIXED"
scene.render.threads = 4
scene.render.resolution_x = 960
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.image_settings.compression = 85
scene.view_settings.view_transform = "Standard"
scene.world.color = (0.24, 0.24, 0.24)
scene.render.filepath = str(OUTPUT)
bpy.ops.render.render(write_still=True)
