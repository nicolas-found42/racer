#!/usr/bin/env python3
"""Add an explicitly authored plate to the pinned Roadster preview."""
import argparse
import copy
import hashlib
import io
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from install_cars import regular_bytes
from prepare_gt4_vehicle import pack, unpack
from prepare_source_bump import publish, safe

MESH_SHA = '5b93b861a31ce8d4da014e80a14f86bb98b7b5be096dd7e152f6ca0ea0ff9220'
DESCRIPTOR_SHA = 'b2456ac4bc6f6b364168c33944d84bef83cde904ac1bfaec8d03360dfefdffd3'
FONT_SHA = 'd72db21f9242aedd6b917d8549ad5921766b24d5f8d0becfda2ff4c620b3c2e0'
MATERIAL = 'vp_nsn_350z_06/resources/vehicle/vp_nsn_350z_06/bumper_r0_lod_0.xrsc/shader30'
POLICY = ('Racer-authored RCR350 plate, typography, border and fasteners. '
          'Not a recovered native registration or LicensePlate shader. '
          'Native background/font samplers are unbound in the vehicle pack; '
          'their runtime textures and text mapping remain unknown.')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def plate_image(font_bytes):
    require(sha(font_bytes) == FONT_SHA, 'font_pin')
    # The raster is generated here; no font file is copied into the asset.
    image = Image.new('RGBA', (512, 256), (234, 235, 224, 255))
    draw = ImageDraw.Draw(image)
    for y in range(256):
        shade = round(242 - 13 * y / 255)
        draw.line((0, y, 511, y), fill=(shade, shade + 1, shade - 8, 255))
    draw.rounded_rectangle((5, 5, 506, 250), radius=17, outline=(66, 72, 75), width=5)
    draw.rounded_rectangle((16, 16, 495, 239), radius=9, outline=(26, 48, 75), width=3)
    title = ImageFont.truetype(io.BytesIO(font_bytes), 30)
    number = ImageFont.truetype(io.BytesIO(font_bytes), 106)
    draw.text((256, 36), 'RACER', font=title, anchor='mm', fill=(143, 30, 32))
    draw.text((256, 144), 'RCR350', font=number, anchor='mm', fill=(20, 37, 59))
    for x in (43, 469):
        for y in (40, 216):
            draw.ellipse((x - 6, y - 6, x + 6, y + 6), fill=(105, 110, 112), outline=(207, 210, 205), width=2)
            draw.line((x - 3, y, x + 3, y), fill=(40, 46, 47), width=2)
    encoded = io.BytesIO()
    image.save(encoded, format='PNG')
    return encoded.getvalue()


def append_plate(doc, binary, png):
    """Preserve the complete source prefix; change one primitive's binding."""
    uses = [(mi, pi) for mi, mesh in enumerate(doc['meshes'])
            for pi, primitive in enumerate(mesh['primitives'])
            if primitive.get('material') == 34]
    require(uses == [(22, 0)], 'plate_primitive_identity')
    material = doc['materials'][34]
    require(material.get('name') == MATERIAL and material.get('extras') ==
            {'sourceShader': 'LicensePlate', 'sourceDrawBucket': 1}, 'plate_material_identity')
    require(material.get('alphaMode') == 'OPAQUE' and material.get('pbrMetallicRoughness') ==
            {'baseColorFactor': [.8, .8, .8, 1.0], 'metallicFactor': 0.0,
             'roughnessFactor': .7}, 'plate_original_recipe')
    primitive = doc['meshes'][22]['primitives'][0]
    require(set(primitive['attributes']) == {'POSITION', 'NORMAL', 'TEXCOORD_0'}, 'plate_attributes')
    require(doc['accessors'][primitive['attributes']['POSITION']]['count'] == 4 and
            doc['accessors'][primitive['indices']]['count'] == 6, 'plate_quad')
    with Image.open(io.BytesIO(png)) as image:
        require(image.format == 'PNG' and image.mode == 'RGBA' and image.size == (512, 256), 'plate_pixels')
        require(image.getchannel('A').getextrema() == (255, 255), 'plate_coverage')
    result = copy.deepcopy(doc)
    blob = bytearray(binary)
    blob.extend(b'\0' * (-len(blob) % 4))
    view = len(result['bufferViews'])
    result['bufferViews'].append({'buffer': 0, 'byteOffset': len(blob), 'byteLength': len(png)})
    blob.extend(png)
    image_index = len(result.setdefault('images', []))
    result['images'].append({'bufferView': view, 'mimeType': 'image/png', 'name': 'Racer authored RCR350 plate'})
    sampler = len(result.setdefault('samplers', []))
    result['samplers'].append({'wrapS': 33071, 'wrapT': 33071, 'minFilter': 9987, 'magFilter': 9729})
    texture = len(result.setdefault('textures', []))
    result['textures'].append({'source': image_index, 'sampler': sampler})
    clone = copy.deepcopy(material)
    clone['pbrMetallicRoughness'] = {'baseColorFactor': [1, 1, 1, 1],
        'baseColorTexture': {'index': texture}, 'metallicFactor': 0, 'roughnessFactor': .45}
    clone['extras']['racerAuthoredPlate'] = {'policy': POLICY, 'sourceMaterial': 34,
        'pngSha256': sha(png), 'fontSha256': FONT_SHA, 'dimensions': [512, 256]}
    material_index = len(result['materials'])
    result['materials'].append(clone)
    result['meshes'][22]['primitives'][0]['material'] = material_index
    result['buffers'][0]['byteLength'] = len(blob)
    restored = copy.deepcopy(result['meshes'])
    restored[22]['primitives'][0]['material'] = 34
    require(restored == doc['meshes'] and blob[:len(binary)] == binary, 'geometry_prefix')
    for key in ('nodes', 'scenes', 'scene', 'accessors', 'extras', 'extensionsUsed', 'extensionsRequired'):
        require(result.get(key) == doc.get(key), 'source_structure_' + key)
    for key in ('materials', 'images', 'textures', 'samplers', 'bufferViews'):
        require(result[key][:len(doc.get(key, []))] == doc.get(key, []), 'source_prefix_' + key)
    return result, blob


def build(mesh, descriptor, font):
    require(sha(mesh) == MESH_SHA and sha(descriptor) == DESCRIPTOR_SHA, 'vehicle_input_pin')
    png = plate_image(font)
    doc, binary = unpack(mesh)
    result, blob = append_plate(doc, binary, png)
    glb = pack(result, blob)
    require(len(glb) <= 8 * 1024**2, 'mesh_budget')
    digest = sha(glb)
    replacements = {'id': 'id ' + json.dumps('vehicle-' + digest),
                    'mesh': 'mesh ' + json.dumps(digest + '.glb'), 'sha256': 'sha256 ' + digest}
    lines = descriptor.decode().splitlines()
    require(sum(line.startswith('sha256 ') for line in lines) == 1 and
            'sha256 ' + MESH_SHA in lines, 'descriptor_binding')
    derived = ('\n'.join(replacements.get(line.split(' ', 1)[0], line) for line in lines) + '\n').encode()
    manifest = {'policy': POLICY, 'input_mesh_sha256': MESH_SHA, 'input_descriptor_sha256': DESCRIPTOR_SHA,
                'mesh_sha256': digest, 'png_sha256': sha(png), 'font_sha256': FONT_SHA,
                'geometry': 'Original BIN prefix, arrays, nodes and every other primitive/material binding unchanged.',
                'bytes': len(glb), 'decoded_plate_bytes': 512 * 256 * 4}
    return {digest + '.glb': glb, digest + '.vehicle': derived,
            'catalog.racer': ('RACER_VEHICLES 1\n1\n' + json.dumps(digest + '.vehicle') + '\n').encode(),
            'plate.png': png, 'manifest.json': (json.dumps(manifest, indent=2) + '\n').encode()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('mesh', 'descriptor', 'font', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    files = build(regular_bytes(safe(args.mesh), 8 * 1024**2),
                  regular_bytes(safe(args.descriptor), 16384),
                  regular_bytes(safe(args.font), 1024**2))
    publish(args.output, files)
    print(json.dumps({'catalog': str(args.output / 'catalog.racer'), 'policy': POLICY}))


if __name__ == '__main__':
    main()
