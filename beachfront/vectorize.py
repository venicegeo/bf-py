"""
beachfront-py
https://github.com/venicegeo/beachfront-py

Copyright 2016, RadiantBlue Technologies, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import json
import logging
from osgeo import osr
import potrace as _potrace
from pyproj import Proj, transform
import fiona
from fiona.crs import from_epsg

logger = logging.getLogger('beachfront')


def lines_to_features(lines, source='imagery'):
    """ Create features from lines """
    gid = 0
    features = []
    for line in lines:
        feature = {
            'type': 'Feature',
            'geometry': {
                'type': 'LineString',
                'coordinates': line
            },
            'properties': {
                'id': gid,
                'source': source
            }
        }
        features.append(feature)
        gid += 1
    return features


def save_shapefile(lines, fout, source='imagery'):
    """ Create shapefile - NOTE: Currently assumes EPSG:4326! """
    schema = {
        'geometry': 'LineString',
        'properties': {
            'id': 'int',
            'source': 'str:24',
        }
    }
    features = lines_to_features(lines, source=source)
    # TODO - get epsg from geojson
    crs = from_epsg(4326)
    with fiona.open(fout, 'w', 'ESRI Shapefile', schema, crs=crs) as output:
        output.writerecords(features)


def to_geojson(lines, source='imagery'):
    geojson = {
        'type': 'FeatureCollection',
        'features': lines_to_features(lines, source=source),
    }
    return geojson


def save_geojson(lines, fout, source='imagery'):
    """ Save lines as GeoJSON file """
    geojson = to_geojson(lines, source=source)
    with open(fout, 'w') as f:
        f.write(json.dumps(geojson))
    return fout


def potrace_array(arr, minsize=10.0, tolerance=0.2, alphamax=0.0, opticurve=1):
    """ Trace numpy array using potrace """
    # tolerance, alphamax, and opticurve are best kept at their defaults
    bmp = _potrace.Bitmap(arr)
    logger.debug('potrace: minsize=%s, tolerance=%s, alphamax=%s, opticurve=%s' %
                 (minsize, tolerance, alphamax, opticurve))
    polines = bmp.trace(turdsize=minsize, turnpolicy=_potrace.TURNPOLICY_WHITE,
                        alphamax=alphamax, opticurve=opticurve, opttolerance=tolerance)
    lines = []
    for line in polines:
        lines.append(line.tesselate().tolist())

    return lines


def filter_nodata_lines(lines, mask, dist=5):
    """ Remove nodes within dist pixels of nodata regions or scene edges, splitting lines as needed  """
    #if mask.max() == 0:
    #    raise Exception('Empty mask!')
    newlines = []
    logger.debug('%s lines before filtering and splitting' % len(lines))
    xsize = mask.shape[0]
    ysize = mask.shape[1]
    minloc = 2
    xmaxloc = xsize - minloc - 1
    ymaxloc = ysize - minloc - 1
    for line in lines:
        startloc = 0
        for loc in range(0, len(line)):
            # check if this is masked point
            locx = int(line[loc][1])
            locy = int(line[loc][0])
            m = mask[max(locx-dist, 0):min(locx+dist, mask.shape[0]),
                     max(locy-dist, 0):min(locy+dist, mask.shape[1])]
            if m.sum() or (locx < minloc) or (locy < minloc) or (locx > xmaxloc) or (locy > ymaxloc):
                if (loc-startloc) > 1:
                    newlines.append(line[startloc:loc])
                startloc = loc + 1
        # add the last segment
        if (loc-startloc) > 1:
            newlines.append(line[startloc:])
    logger.debug('%s lines after filtering and splitting' % len(newlines))
    return newlines


def potrace(geoimg, geoloc=False, **kwargs):
    """ Trace raster image using potrace and return geolocated or lat-lon coordinates """
    # assuming single band
    arr = geoimg.read()
    mask = geoimg.nodata_mask()

    arr[mask == 1] = 0
    lines = potrace_array(arr, **kwargs)

    lines = filter_nodata_lines(lines, mask)

    if not geoloc:
        srs = osr.SpatialReference(geoimg.srs()).ExportToProj4()
        projin = Proj(srs)
        projout = Proj(init='epsg:4326')
    newlines = []
    for line in lines:
        newline = []
        for point in line:
            pt = geoimg.geoloc(point[0], point[1])
            pt = [pt.x(), pt.y()]
            if not geoloc:
                # convert to lat-lon
                pt = transform(projin, projout, pt[0], pt[1])
            newline.append(pt)
        newlines.append(newline)

    return newlines
