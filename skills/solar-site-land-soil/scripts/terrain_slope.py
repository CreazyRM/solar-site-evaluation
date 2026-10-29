"""Reusable offline parcel slope worker; NumPy and Pillow are optional dependencies.

The CLI returns compact JSON. The array calculation can also be imported by a web
backend. Supports north-up, PixelIsArea GeoTIFFs in metre-based UTM coordinates.
No network calls, implicit reprojection or package installation are performed.
"""
import argparse
import hashlib
import json
import math
import time
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import assess

VERSION = "1.0"
ACRE_M2 = 4046.8564224

def check_rings(rings):
    if not rings:
        raise ValueError("Boundary has no rings.")
    for ring in rings:
        if len(ring) < 4 or ring[0] != ring[-1]:
            raise ValueError("Boundary rings must be closed with at least four vertices.")
        if any(len(p) != 2 or not all(isinstance(v, (int,float)) and math.isfinite(v) for v in p) for p in ring):
            raise ValueError("Boundary vertices must have two finite projected coordinates.")
        if abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(ring,ring[1:]))) < 1e-8:
            raise ValueError("Boundary ring has zero area.")

def inside_ring(x, y, ring):
    """Even-odd cell-centre inclusion; ring winding does not change inclusion."""
    inside = np.zeros(np.broadcast_shapes(x.shape,y.shape), dtype=bool)
    for a,b in zip(ring,ring[1:]):
        if a[1] != b[1]:
            inside ^= ((a[1]>y)!=(b[1]>y)) & (x < (b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0])
    return inside

def horn_slope(z, dx, dy):
    """Percent grade on a 3x3 Horn kernel; all nine cells must be valid."""
    z = np.asarray(z, dtype=float)
    result = np.full(z.shape,np.nan)
    a,b,c = z[:-2,:-2],z[:-2,1:-1],z[:-2,2:]
    d,e,f = z[1:-1,:-2],z[1:-1,1:-1],z[1:-1,2:]
    g,h,i = z[2:,:-2],z[2:,1:-1],z[2:,2:]
    gx = ((c+2*f+i)-(a+2*d+g))/(8*dx)
    gy = ((g+2*h+i)-(a+2*b+c))/(8*dy)
    valid = np.logical_and.reduce([np.isfinite(q) for q in (a,b,c,d,e,f,g,h,i)])
    result[1:-1,1:-1] = np.where(valid,100*np.hypot(gx,gy),np.nan)
    return result

def analyze(z, rings, xmin, ymax, dx, dy, cutoff=15, nodata=None, vertical_scale=1):
    """Calculate masked statistics from metre-based projected geometry and grid.

    Preserve the surrounding DTM halo for gradient calculation, then include only
    parcel cell centres in statistics. A NoData hole excludes its full 3x3 kernel.
    """
    check_rings(rings)
    if any(not math.isfinite(v) for v in (xmin,ymax,dx,dy,cutoff,vertical_scale)) or min(dx,dy,vertical_scale)<=0 or cutoff<0:
        raise ValueError("Grid sizes and vertical scale must be positive; cutoff must be nonnegative.")
    z = np.array(z,dtype=float,copy=True)
    if z.ndim != 2 or min(z.shape)<3:
        raise ValueError("Terrain must be a single-band grid at least 3x3 cells.")
    height,width = z.shape
    xmax,ymin = xmin+width*dx,ymax-height*dy
    if any(not(xmin-1e-7 <= p[0] <= xmax+1e-7 and ymin-1e-7 <= p[1] <= ymax+1e-7) for r in rings for p in r):
        raise ValueError("Boundary extends beyond raster extent; full-parcel coverage cannot be claimed.")
    z[~np.isfinite(z) | (np.abs(z)>1e30)] = np.nan
    if nodata is not None:
        z[z==nodata] = np.nan
    z *= vertical_scale
    x = xmin+(np.arange(width)[None,:]+.5)*dx
    y = ymax-(np.arange(height)[:,None]+.5)*dy
    mask = np.zeros(z.shape,dtype=bool)
    for ring in rings:
        mask ^= inside_ring(x,y,ring)
    if not mask.any():
        raise ValueError("No raster cell centres fall inside the boundary.")
    slope = horn_slope(z,dx,dy)
    valid = mask & np.isfinite(slope)
    if not valid.any():
        raise ValueError("No parcel cells have a complete valid slope kernel.")
    grades = slope[valid]
    above = valid & (slope>cutoff)
    stats = {"method":"Horn 3x3; percent grade = 100 * hypot(dz/dx, dz/dy)",
        "processing_pixel_size_m":[dx,dy],"parcel_cells":int(mask.sum()),"valid_parcel_cells":int(valid.sum()),
        "coverage_percent":100*float(valid.sum())/int(mask.sum()),
        "assessed_area_square_metres":int(valid.sum())*dx*dy,
        "elevation_min_m":float(z[valid].min()),"elevation_max_m":float(z[valid].max()),
        "mean_slope_percent":float(grades.mean()),"median_slope_percent":float(np.median(grades)),
        "p95_slope_percent":float(np.percentile(grades,95)),"maximum_slope_percent":float(grades.max()),
        "cutoff_percent":cutoff,"cutoff_comparison":"strictly greater than",
        "above_cutoff_cells":int(above.sum()),"area_above_cutoff_square_metres":int(above.sum())*dx*dy,
        "area_above_cutoff_acres":int(above.sum())*dx*dy/ACRE_M2,
        "fraction_above_cutoff":float(above.sum())/int(valid.sum()),"overall_parcel_pass":None}
    return stats,slope,mask,valid

def read_geotiff(path):
    """Read spatial metadata instead of guessing pixels or units from a filename."""
    with Image.open(path) as image:
        tags = image.tag_v2
        if tags.get(34264):
            raise ValueError("Affine/rotated GeoTIFF is unsupported; provide a north-up UTM export.")
        scale,tie,keys = tags.get(33550),tags.get(33922),tags.get(34735)
        if not scale or not tie or not keys:
            raise ValueError("Missing GeoTIFF scale, tiepoint or CRS keys.")
        geo = {keys[i]:keys[i+3] for i in range(4,len(keys),4) if keys[i+1]==0 and keys[i+2]==1}
        epsg = geo.get(3072)
        supported = isinstance(epsg,int) and (26901<=epsg<=26923 or 32601<=epsg<=32660 or 32701<=epsg<=32760 or 25828<=epsg<=25838)
        if geo.get(1024)!=1 or not supported or geo.get(3076,9001)!=9001 or geo.get(1025,1)!=1:
            raise ValueError("Require PixelIsArea, projected metre-based UTM; geographic/Web Mercator/feet are unsupported.")
        if len(tie)!=6 or scale[0]<=0 or scale[1]<=0:
            raise ValueError("Unsupported GeoTIFF tiepoints or pixel scale.")
        grid = np.asarray(image,dtype=float)
        nodata = tags.get(42113)
        if isinstance(nodata,bytes):
            nodata = nodata.decode("ascii").strip("\x00")
        nodata = float(str(nodata).strip("\x00")) if nodata is not None else None
        metadata = {"epsg":epsg,"xmin":tie[3]-tie[0]*scale[0],"ymax":tie[4]+tie[1]*scale[1],"dx":scale[0],"dy":scale[1],"nodata":nodata}
    return grid,metadata

def read_boundary(path, expected_epsg):
    """Accept projected Esri rings or the saved public GeometryServer response."""
    raw = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    geometry = raw
    if "data" in raw and "geometries" in raw["data"]:
        if len(raw["data"]["geometries"])!=1:
            raise ValueError("Expected one projected parcel geometry.")
        geometry = raw["data"]["geometries"][0]
    epsg = geometry.get("spatialReference",{}).get("latestWkid",geometry.get("spatialReference",{}).get("wkid"))
    if epsg is None:
        epsg = raw.get("request",{}).get("outSR")
    if str(epsg)!=str(expected_epsg):
        raise ValueError("Boundary CRS must explicitly match raster EPSG; no implicit reprojection.")
    rings = geometry.get("rings")
    check_rings(rings)
    return rings

def save_map(path,slope,valid,rings,grid,cutoff):
    rgba = np.zeros((*slope.shape,4),dtype=np.uint8)
    rgba[valid & (slope<=5)]=[206,237,213,255]
    rgba[valid & (slope>5) & (slope<=10)]=[102,183,143,255]
    rgba[valid & (slope>10)]=[246,206,102,255]
    rgba[valid & (slope>cutoff)]=[206,67,65,255]
    canvas=Image.new("RGB",(1000,1020),"#f3f5f7")
    layer=Image.fromarray(rgba)
    factor=min(900/layer.width,780/layer.height)
    size=(max(1,round(layer.width*factor)),max(1,round(layer.height*factor)))
    layer=layer.resize(size,Image.Resampling.NEAREST)
    left,top=(1000-size[0])//2,80
    canvas.paste(layer,(left,top),layer)
    draw=ImageDraw.Draw(canvas)
    font=ImageFont.load_default(size=20)
    draw.text((30,20),f"Parcel slope | EPSG:{grid['epsg']} | North up",font=font,fill="#18384f")
    for ring in rings:
        vertices=[(left+(p[0]-grid['xmin'])/grid['dx']*factor,top+(grid['ymax']-p[1])/grid['dy']*factor) for p in ring]
        draw.line(vertices,fill="#273b51",width=2)
    draw.text((30,885),f"Red: strictly above {cutoff:g}% grade. Outline: supplied parcel.",font=font,fill="#18384f")
    draw.text((30,920),"Transparent cells: outside parcel or slope unavailable.",font=font,fill="#18384f")
    draw.text((30,955),"Terrain colours: <=5% pale green; >5-10% green; other valid cells yellow.",font=font,fill="#18384f")
    canvas.save(path)

def run_job(terrain,boundary,out,vertical_unit,cutoff=15,nodata=None,source_metadata=None):
    """File adapter for CLI/backend callers; returns only summary and artifact paths."""
    started=time.perf_counter()
    if vertical_unit not in ("metres","feet"):
        raise ValueError("Explicit elevation unit must be metres or feet.")
    z,grid=read_geotiff(terrain)
    rings=read_boundary(boundary,grid["epsg"])
    stats,slope,mask,valid=analyze(z,rings,grid["xmin"],grid["ymax"],grid["dx"],grid["dy"],cutoff,
                                 nodata if nodata is not None else grid["nodata"],1 if vertical_unit=="metres" else .3048)
    out=Path(out)
    out.mkdir(parents=True,exist_ok=True)
    source=json.loads(Path(source_metadata).read_text(encoding="utf-8-sig")) if source_metadata else {}
    manifest={"worker_version":VERSION,"generated_at":assess.utc_now(),"epsg":grid["epsg"],"vertical_unit_input":vertical_unit,
              "source":source.get("source"),"source_retrieved_at":source.get("retrieved_at"),"acquisition_date":None,
              "inputs":[{"path":str(Path(p).resolve()),"sha256":hashlib.sha256(Path(p).read_bytes()).hexdigest()} for p in (terrain,boundary)],
              "statistics":stats,"limitations":["Cell-centre clipping and raster resolution affect area estimates.",
              "Coverage is valid 3x3 slope kernels divided by parcel raster cells; unavailable cells are not flat.",
              "Terrain source acquisition date is unresolved; this run reuses saved data.",
              "No soil/wetland deductions, engineering approval or overall project Pass/Fail."]}
    assess.save_json(out/"slope-statistics.json",manifest)
    save_map(out/"slope-map.png",slope,valid,rings,grid,cutoff)
    lines=["# Parcel Slope Worker Result","",f"Generated: {manifest['generated_at']}","",f"Coverage: {stats['coverage_percent']:.2f}%",
        f"Mean / median slope: {stats['mean_slope_percent']:.2f}% / {stats['median_slope_percent']:.2f}%",
        f"95th percentile: {stats['p95_slope_percent']:.2f}%",
        f"Area above {cutoff:g}%: {stats['area_above_cutoff_square_metres']:.0f} m2 / {stats['area_above_cutoff_acres']:.3f} acres",
        f"Fraction of assessed cells above cutoff: {100*stats['fraction_above_cutoff']:.2f}%","",
        "![Slope map](slope-map.png)","","## Limitations","",*['- '+s for s in manifest['limitations']],""]
    (out/"report.md").write_text("\n\n".join(lines),encoding="utf-8")
    summary={"status":"completed" if stats['coverage_percent']==100 else "needs_review","duration_seconds":round(time.perf_counter()-started,4),
        "coverage_percent":stats['coverage_percent'],"mean_slope_percent":stats['mean_slope_percent'],
        "area_above_cutoff_acres":stats['area_above_cutoff_acres'],"fraction_above_cutoff":stats['fraction_above_cutoff'],
        "warnings":["Saved terrain; acquisition date unknown"]+([] if stats['coverage_percent']==100 else ["Incomplete slope coverage"]),
        "artifacts":{k:str((out/v).resolve()) for k,v in [("statistics","slope-statistics.json"),("map","slope-map.png"),("report","report.md")]}}
    assess.save_json(out/"task-summary.json",summary)
    return summary

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--terrain",required=True)
    parser.add_argument("--boundary",required=True)
    parser.add_argument("--vertical-unit",choices=["metres","feet"],required=True)
    parser.add_argument("--cutoff",type=float,default=15)
    parser.add_argument("--nodata",type=float)
    parser.add_argument("--source-metadata")
    parser.add_argument("--out",required=True)
    args=parser.parse_args()
    try:
        result=run_job(args.terrain,args.boundary,args.out,args.vertical_unit,args.cutoff,args.nodata,args.source_metadata)
    except (ValueError,OSError,KeyError,TypeError) as exc:
        result={"status":"needs_review","reason":str(exc)}
        print(json.dumps(result,allow_nan=False))
        raise SystemExit(2)
    print(json.dumps(result,allow_nan=False))

if __name__=="__main__":
    main()
