"""Analytical, coverage and missing-data tests for the offline slope worker."""
import math
import unittest
import json
from unittest.mock import patch
import numpy as np
from terrain_slope import analyze, horn_slope, read_boundary

def ring(x0,y0,x1,y1):
    return [[x0,y0],[x1,y0],[x1,y1],[x0,y1],[x0,y0]]

class TerrainTests(unittest.TestCase):
    def test_plane_and_unequal_pixels(self):
        x,y=np.meshgrid(np.arange(9)*3.,np.arange(9)*2.)
        actual=horn_slope(.1*x+.2*y,3,2)
        self.assertTrue(np.allclose(actual[1:-1,1:-1],100*math.hypot(.1,.2)))
        self.assertTrue(np.isnan(actual[0,:]).all())

    def test_exact_cutoff_is_not_adverse(self):
        z=np.tile(np.arange(10)*3.,(10,1))
        stats,*_=analyze(z,[ring(20,20,180,180)],0,200,20,20,15)
        self.assertEqual(stats['coverage_percent'],100)
        self.assertEqual(stats['mean_slope_percent'],15)
        self.assertEqual(stats['above_cutoff_cells'],0)
        stats,*_=analyze(z,[ring(20,20,180,180)],0,200,20,20,14.9)
        self.assertEqual(stats['fraction_above_cutoff'],1)

    def test_holes_and_disjoint_parts(self):
        stats,*_=analyze(np.zeros((9,9)),[ring(1,1,8,8),ring(3,3,6,6)],0,9,1,1)
        self.assertEqual(stats['parcel_cells'],40)
        reversed_stats,*_=analyze(np.zeros((9,9)),[list(reversed(ring(1,1,8,8))),ring(3,3,6,6)],0,9,1,1)
        self.assertEqual(stats,reversed_stats)
        parts,*_=analyze(np.zeros((9,9)),[ring(1,1,3,3),ring(6,6,8,8)],0,9,1,1)
        self.assertEqual(parts['parcel_cells'],8)

    def test_nodata_center_invalidates_full_kernel(self):
        z=np.zeros((9,9));z[4,4]=-9999
        stats,_,_,valid=analyze(z,[ring(1,1,8,8)],0,9,1,1,nodata=-9999)
        self.assertEqual(stats['valid_parcel_cells'],40)
        self.assertFalse(valid[4,4])
        self.assertAlmostEqual(stats['coverage_percent'],100*40/49)
        self.assertFalse(valid[3:6,3:6].any())

    def test_units_convert_before_gradient(self):
        z=np.tile(np.arange(9)*10.,(9,1))
        metres,*_=analyze(z,[ring(1,1,8,8)],0,9,1,1)
        feet,*_=analyze(z,[ring(1,1,8,8)],0,9,1,1,vertical_scale=.3048)
        self.assertAlmostEqual(feet['mean_slope_percent'],metres['mean_slope_percent']*.3048)

    def test_invalid_geometry_and_incomplete_extent(self):
        for rings in ([ring(-1,1,8,8)],[[[1,1],[2,1],[2,2],[1,2]]],[[[1,1],[2,2],[3,3],[1,1]]]):
            with self.assertRaises(ValueError):
                analyze(np.zeros((9,9)),rings,0,9,1,1)
        with self.assertRaises(ValueError):
            analyze(np.full((9,9),np.nan),[ring(1,1,8,8)],0,9,1,1)

    def test_boundary_crs_must_match(self):
        data={"rings":[ring(1,1,8,8)],"spatialReference":{"wkid":4326}}
        with patch('terrain_slope.Path.read_text',return_value=json.dumps(data)):
            with self.assertRaises(ValueError):
                read_boundary('synthetic.json',26917)
        data['spatialReference']['wkid']=26917
        with patch('terrain_slope.Path.read_text',return_value=json.dumps(data)):
            self.assertEqual(read_boundary('synthetic.json',26917),data['rings'])

if __name__=='__main__':
    unittest.main(verbosity=2)
