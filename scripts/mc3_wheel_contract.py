#!/usr/bin/env python3
"""MC3 static wheel alias binding by proven bone pose, never numeric-name order.

Callers must supply an independently decoded, source-identified native skeleton.
This contract establishes static ownership only, not playable status or units.
"""
import math,re
from prepare_gt4_vehicle import require,finite_vector
LABELS=('FL','FR','RL','RR')
ALIAS=re.compile(r'(?:whl_?0?[0-3]|wheel[0-3]|whl[fr][01])',re.I)

def resolve(doc,native_bones):
    e=doc.get('extras',{});require(e.get('source_profile')=='mc3-ps2-static-preview-v1','mc3_profile')
    require(isinstance(native_bones,list)and 0<len(native_bones)<=4096,'native_bone_budget')
    bones={b['index']:b for b in native_bones};require(len(bones)==len(native_bones),'duplicate_bone_index')
    preview=e.get('nativeSkeleton',{}).get('bones',[]);require(len(preview)==len(bones)and {b.get('index')for b in preview}==set(bones),'native_skeleton_join')
    for b in preview:
        require(b.get('index')in bones,'native_skeleton_join');actual=bones[b['index']]
        for key in('name','parent','global_position','local_position','rotation_raw'):
            a=actual.get(key);v=b.get(key)
            require(list(a)==list(v)if isinstance(a,(tuple,list))and isinstance(v,(tuple,list))else a==v,'native_skeleton_join')
    def named(name):
        rows=[b for b in native_bones if b['name']==name];require(len(rows)==1,'orientation_anchor_missing');return rows[0]
    # Native body labels provide the frame independently of wheel alias spelling.
    def alias(names):
        rows=[b for b in native_bones if b['name'] in names]
        require(len(rows)<=1,'ambiguous_orientation_alias')
        return rows[0] if rows else None
    hood=alias(('hood','hoods','hoodbone'));trunk=alias(('trunkbone','trunk','trunk_bne','tk'));left=named('Arm_Front_L');right=named('Arm_Front_R')
    # Other shipped skeletons use a zero-position kit hood or short part labels.
    # Explicit front/rear suspension labels establish the same static axis.
    if hood is None or trunk is None:
        hood=left;trunk=named('Arm_Rear_L')
    hp=finite_vector(hood['global_position'],3);tp=finite_vector(trunk['global_position'],3);lp=finite_vector(left['global_position'],3);rp=finite_vector(right['global_position'],3)
    require(hp[2]<-.1 and tp[2]>.1 and abs(hp[2]-tp[2])>max(abs(hp[i]-tp[i])for i in(0,1)),'ambiguous_front_axis')
    require(lp[0]<-.01 and rp[0]>.01 and abs(lp[0]-rp[0])>max(abs(lp[i]-rp[i])for i in(1,2)),'ambiguous_side_axis')
    scene=doc.get('scenes',[]);require(len(scene)>doc.get('scene',0),'scene');active=scene[doc.get('scene',0)]['nodes'];require(len(active)<=4095 and len(active)==len(set(active)),'active_node_budget')
    ownership={};centers={};components={};bone_slots={};evidence=[]
    for index in active:
        require(type(index)is int and 0<=index<len(doc['nodes']),'node_index');node=doc['nodes'][index];info=node.get('extras',{});joint=info.get('nativeWheelJoint')
        if joint is None:
            require('nativeWheelComponent'not in info,'wheel_component_without_joint');ownership[index]=-1;continue
        require(isinstance(joint,str)and ALIAS.fullmatch(joint)is not None,'unproved_joint_alias')
        bone_index=info.get('nativeBone');require(type(bone_index)is int and bone_index in bones,'wheel_bone');bone=bones[bone_index];require(bone['name']==joint,'joint_name_join')
        # Zero rest rotations avoid silently ignoring camber/steering ancestors.
        ancestor=bone;seen=set()
        while ancestor is not None:
            require(ancestor['index']not in seen,'bone_cycle');seen.add(ancestor['index']);require(all(abs(v)<1e-8 for v in finite_vector(ancestor['rotation_raw'],3)),'rotated_wheel_frame');parent=ancestor['parent'];require(parent is None or parent in bones,'bone_parent');ancestor=bones[parent]if parent is not None else None
        c=finite_vector(bone['global_position'],3);t=finite_vector(node.get('translation'),3);require(max(abs(c[i]-t[i])for i in range(3))<1e-7,'wheel_pose_join')
        require(c[1]>0 and abs(c[0])>.05 and abs(c[2])>.1,'ambiguous_wheel_pose');slot=(0 if c[2]<0 else 2)+(0 if c[0]<0 else 1)
        require(slot not in centers or centers[slot]==c,'duplicate_slot_pose');require(bone_index not in bone_slots or bone_slots[bone_index]==slot,'split_bone_slot');bone_slots[bone_index]=slot
        kind=info.get('nativeWheelComponent');require(kind in('rim','tire')and(slot,kind)not in components,'component_ownership');components[slot,kind]=index;ownership[index]=slot;centers[slot]=c
        evidence.append({'node':index,'native_bone_index':bone_index,'native_joint_name':joint,'canonical_slot':LABELS[slot],'component':kind,'native_position':c})
    require(set(centers)==set(range(4))and len(bone_slots)==4 and len(components)==8,'four_complete_wheels')
    for front in(0,2):
        a,b=centers[front],centers[front+1];require(abs(a[1]-b[1])<.02 and abs(a[2]-b[2])<.02,'unpaired_axle')
    return {'ownership':ownership,'centers':centers,'evidence':evidence,'orientation_anchors':{'front':hood['index'],'rear':trunk['index'],'left':left['index'],'right':right['index']},'frame':'Native +X right, +Y retained, -Z front supported by selected body/arm labels and static poses. Racer +Z requires the existing adapter reflection.','limits':['Caller must establish native artifact/hash identity; a supplied skeleton alone is not authoritative.','Alias names are accepted labels only; slot comes from source bone identity and pose, not spelling or ordinal.','Only zero-rotation, four paired rim/tire static assemblies with these explicit orientation anchors are supported.','No unit, physical dimensions, original runtime steering/frame semantics, or player eligibility proof.']}
