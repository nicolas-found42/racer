#!/usr/bin/env python3
"""Source-independent analytic triangle/slab/projected-cylinder tests."""
import math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from slrr_clearance import triangle_clearance,clip_axial,projected_distance
class Checks(unittest.TestCase):
    def test_interior_crossing_no_vertex_inside(self):
        triangle=((0,-2,-2),(0,2,-2),(0,0,2))
        self.assertEqual(triangle_clearance(triangle,(0,0,0),0,.1,.5),-.5)
    def test_outside_axial_slab(self):
        self.assertTrue(math.isinf(triangle_clearance(((1,0,0),(1,1,0),(1,0,1)),(0,0,0),0,.1,.5)))
    def test_edge_distance_and_tangency(self):
        triangle=((0,1,-1),(0,1,1),(0,2,0))
        self.assertAlmostEqual(triangle_clearance(triangle,(0,0,0),0,.1,1),0)
        self.assertAlmostEqual(triangle_clearance(triangle,(0,0,0),0,.1,.5),.5)
    def test_slab_clip_finds_crossing(self):
        poly=clip_axial(clip_axial([(-2,-1,0),(2,-1,0),(0,1,0)],.1,1),.1,-1)
        self.assertTrue(all(abs(p[0])<=.1+1e-12 for p in poly));self.assertEqual(projected_distance(poly),0)
    def test_degenerate_segment(self):
        self.assertAlmostEqual(projected_distance([(0,1,-1),(0,1,1)]),1)
    def test_pose_translation_equivariance(self):
        triangle=((0,1,-1),(0,1,1),(0,2,0));offset=(2,3,4)
        translated=tuple(tuple(p[i]+offset[i]for i in range(3))for p in triangle)
        self.assertAlmostEqual(triangle_clearance(triangle,(0,0,0),.2,.1,.5),triangle_clearance(translated,offset,.2,.1,.5))
if __name__=='__main__':unittest.main()
