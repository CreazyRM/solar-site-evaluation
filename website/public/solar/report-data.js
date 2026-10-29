window.SOLAR_REPORT = {
  "address": "019471 Highway 6, Georgian Bluffs, ON N0H 2T0",
  "evidence_date": "2026-10-09",
  "aliases": [
    "019471 Highway 6",
    "19471 Highway 6",
    "019471 Highway 6, Georgian Bluffs",
    "19471 Highway 6, Georgian Bluffs",
    "019471 Highway 6, Georgian Bluffs, ON",
    "019471 Highway 6, Georgian Bluffs, ON N0H 2T0",
    "19471 Highway 6, Georgian Bluffs, ON N0H2T0",
    "019471 Highway 6, Georgian Bluffs, Ontario N0H 2T0"
  ],
  "metrics": [
    {
      "label": "Measured parcel area",
      "value": "64.949",
      "unit": "acres",
      "note": "Geodesic · county assessment parcel"
    },
    {
      "label": "Agricultural soil",
      "value": "2 / 3 / 5",
      "unit": "CLI",
      "note": "Classes 2 & 3 need exception review"
    },
    {
      "label": "Mean terrain slope",
      "value": "4.57",
      "unit": "%",
      "note": "Full parcel · 2 m processing grid"
    },
    {
      "label": "Above 15% slope",
      "value": "2.08",
      "unit": "%",
      "note": "1.351 acres of assessed cells"
    }
  ],
  "sections": [
    {
      "id": "land",
      "number": "01",
      "kicker": "THE PARCEL",
      "title": "Land & location",
      "status": "Parcel matched",
      "review": false,
      "intro": "The public county parcel matches the civic address and assessment roll number. Its mapped boundary is the common reference for this report.",
      "facts": [
        [
          "Measured parcel area",
          "64.949 acres / 262,838.54 m²"
        ],
        [
          "County recorded acreage",
          "64.897 acres"
        ],
        [
          "Assessment roll number (ARN)",
          "420362000308200"
        ],
        [
          "PIN / title verification",
          "Not independently verified — skipped"
        ],
        [
          "Jurisdiction",
          "Township of Georgian Bluffs, County of Grey"
        ],
        [
          "Boundary type",
          "Public assessment parcel; not a surveyed ownership boundary"
        ]
      ],
      "callout": "Measured area, recorded acreage and historical acreage differ. None is net developable acreage.",
      "method": "County address and ARN matching, visual comparison and GeometryServer geodesic area. Evidence retained from 2–9 October 2026. Geocoder candidates were inconclusive and were not used as parcel boundaries.",
      "sources": [
        0,
        4
      ]
    },
    {
      "id": "soil",
      "number": "02",
      "kicker": "LAND CAPABILITY & TERRAIN",
      "title": "Soil & slope",
      "status": "Exception review",
      "review": true,
      "intro": "Mapped soil units contain CLI Classes 2, 3 and 5. Terrain is mostly below the 15% screening cutoff, with localized steeper cells.",
      "facts": [
        [
          "Mapped CLI classes",
          "2, 3 and 5"
        ],
        [
          "Mixed mapping unit",
          "Class 3 / Class 5, 50% each within the unit"
        ],
        [
          "Mean / median slope",
          "4.57% / 3.95%"
        ],
        [
          "Area above 15% grade",
          "1.351 acres / 2.08% of assessed cells"
        ],
        [
          "Valid slope coverage",
          "100% of parcel raster cells"
        ],
        [
          "Mapped wetlands",
          "3 polygons intersect the parcel"
        ]
      ],
      "callout": "Classes 2 and 3 require a supported exception under the user’s screening rules. Mixed-unit percentages do not identify component locations or parcel acreage shares. Wetland restrictions remain unresolved.",
      "method": "Horn 3×3 gradient on a saved bare-earth DTM, exported at 2 m in EPSG:26917. Cutoff is strictly greater than 15% grade, not degrees. DTM acquisition date is unknown. No soil or wetland exclusions were deducted. Wetland mapping is not field delineation.",
      "sources": [
        1,
        2,
        3
      ]
    },
    {
      "id": "access",
      "number": "03",
      "kicker": "GETTING TO THE SITE",
      "title": "Access & nearby lines",
      "status": "Estimated evidence",
      "review": true,
      "intro": "Historical imagery shows a track entering the clearing from Highway 6. Dated Street View supports a preliminary interpretation of a nearby three-phase circuit.",
      "facts": [
        [
          "Existing track",
          "Visible in 2015 aerial imagery"
        ],
        [
          "Current truck suitability",
          "Unknown"
        ],
        [
          "Legal entrance / highway permission",
          "Not verified"
        ],
        [
          "Estimated nearby phases",
          "3 — visual estimate, not utility confirmation"
        ],
        [
          "Street-level image date",
          "July 2026"
        ],
        [
          "Road-following connection distance",
          "Not calculated; connection endpoints unconfirmed"
        ]
      ],
      "callout": "A visible entrance does not establish legal or truck access. The apparent circuit is across the highway; its serving feeder, crossing requirements and point of connection remain unconfirmed.",
      "method": "2015 county imagery and a retained July 2026 Google Street View observation. Upper crossarm hardware supports an estimated three-phase interpretation. Voltage and feeder identity were not inferred from the image. No fresh imagery was checked for this page.",
      "sources": [
        4
      ]
    },
    {
      "id": "grid",
      "number": "04",
      "kicker": "CANDIDATE CONNECTIONS",
      "title": "Grid capacity",
      "status": "Site result unknown",
      "review": true,
      "intro": "Actual saved calculator trials passed at 2,000 kW for two candidates. Their service relationship to this property has not been confirmed.",
      "facts": [
        [
          "Project scenario",
          "2,000 kW · exporting · inverter-based solar"
        ],
        [
          "Actual site connection",
          "Unknown — serving feeder unconfirmed"
        ]
      ],
      "table": [
        [
          "HEPWORTH DS · F1",
          "Passed",
          "2,700 kW",
          "2,800 kW"
        ],
        [
          "OWEN SOUND TS · M24",
          "Passed",
          "3,000 kW",
          "Not reached"
        ]
      ],
      "callout": "A candidate calculator pass is not site-specific permission and does not reserve capacity. 3,000 kW is the tested ceiling for Owen Sound, not an exact maximum.",
      "method": "Retained Hydro One web calculator trials dated 9 October 2026. Candidates were tested separately. Hepworth has a 100 kW pass/fail bracket. The actual distributor/serving relationship needs confirmation. Grid data has not been refreshed.",
      "sources": [
        5
      ]
    },
    {
      "id": "planning",
      "number": "05",
      "kicker": "LAND USE & PERMISSIONS",
      "title": "Planning & zoning",
      "status": "Further review",
      "review": true,
      "intro": "The parcel has multiple zoning intersections. Electricity-generation wording must be reconciled with environmental restrictions and the proponent’s proposed use.",
      "facts": [
        [
          "Intersecting zoning codes",
          "EP, EP-12, R1, RU, RU-37"
        ],
        [
          "EP-12 overlap",
          "42.236 acres"
        ],
        [
          "RU-37 overlap",
          "22.383 acres"
        ],
        [
          "County map designations",
          "Hazard Lands, Rural, Wetlands"
        ],
        [
          "Private 2 MW ground-mounted solar",
          "Permission not confirmed"
        ],
        [
          "2026 local Official Plan",
          "Adopted; approval/effect and appeals unconfirmed"
        ]
      ],
      "callout": "EP-12 prohibits development/site alteration in the cited exception. RU-37 includes a mapped wetland restriction. General electricity-generation wording does not demonstrate that these restrictions are overridden.",
      "method": "County zoning polygons were intersected with the parcel and measured geodesically. Small EP, RU and R1 overlaps were retained. Saved By-law 2020-020 provisions and the July 2026 adoption notice were reviewed; later amendments and operative approval status were not conclusively exhausted.",
      "sources": [
        6,
        7,
        8
      ]
    }
  ],
  "sources": [
    {
      "name": "Grey County assessment parcels",
      "url": "https://gis.grey.ca/server/rest/services/Public/Service_ParcelLabels/MapServer/0",
      "note": "Address, ARN and parcel geometry · retained 2–9 Oct 2026"
    },
    {
      "name": "Ontario agricultural soil mapping",
      "url": "https://ws.lioservices.lrc.gov.on.ca/arcgis4/rest/services/AIA/AIA_Map/MapServer/29",
      "note": "CLI mapping units and composition · retained Oct 2026"
    },
    {
      "name": "Ontario wetlands mapping",
      "url": "https://ws.lioservices.lrc.gov.on.ca/arcgis2/rest/services/LIO_OPEN_DATA/LIO_Open01/MapServer/15",
      "note": "Mapped intersections; boundaries and regulatory constraints require review"
    },
    {
      "name": "Ontario lidar-derived DTM",
      "url": "https://ws.geoservices.lrc.gov.on.ca/arcgis5/rest/services/Elevation/Ontario_DTM_LidarDerived/ImageServer",
      "note": "Saved 2 m export · retrieved 2 Oct 2026 · acquisition date unknown"
    },
    {
      "name": "Grey County 2015 aerial imagery",
      "url": "https://gis.grey.ca/server/rest/services/Public/AirPhotos2015/ImageServer",
      "note": "Historical imagery, not present-day site confirmation"
    },
    {
      "name": "Hydro One capacity calculator",
      "url": "https://www.hydroone.com/businessservices_/generators_/Pages/stationcapacitycalculator.aspx",
      "note": "Saved actual candidate trials · 9 Oct 2026 · no capacity reservation"
    },
    {
      "name": "Grey County Georgian Bluffs zoning",
      "url": "https://gis.grey.ca/server/rest/services/Public/Service_GreyCountyZoning/MapServer/1",
      "note": "Parcel intersections · not a determination of permitted use"
    },
    {
      "name": "Georgian Bluffs planning notices",
      "url": "https://www.georgianbluffs.ca/build-and-invest/land-use-planning/public-notices/",
      "note": "Saved 2026 plan adoption notice; approval/effect unconfirmed"
    },
    {
      "name": "Georgian Bluffs zoning by-law",
      "url": "https://www.georgianbluffs.ca/build-and-invest/land-use-planning/zoning-by-law/",
      "note": "By-law 2020-020 and cited exceptions · later amendments not exhausted"
    }
  ],
  "maps": [
    {
      "title": "Aerial",
      "file": "assets/aerial.webp",
      "note": "Red: public county assessment parcel. Grey County aerial imagery dates to 2015. Current conditions and legal access are not established."
    },
    {
      "title": "Soil",
      "file": "assets/soil.webp",
      "note": "Ontario soil capability overlay at 50% opacity on Grey County 2015 imagery. CLI Classes 2, 3 and 5 intersect the red parcel outline; proportions are within mapping units."
    },
    {
      "title": "Wetlands",
      "file": "assets/wetlands.webp",
      "note": "Blue: official mapped wetlands; red: assessment parcel. Three wetland polygons intersect. No regulatory buffers or excluded acreage are shown."
    },
    {
      "title": "Slope",
      "file": "assets/slope.webp",
      "note": "North-up projected terrain, 2 m grid. Red: strictly >15% grade; black outline: supplied parcel. Slope uses a separate map extent; acquisition date remains unknown."
    },
    {
      "title": "Zoning",
      "file": "assets/zoning.webp",
      "note": "Coloured polygons: saved clipped zoning intersections. Red boundary: assessment parcel. Colours distinguish polygons, not development permission. Consult the listed codes and by-law provisions."
    }
  ],
  "structured": {
    "address": "019471 Highway 6, Georgian Bluffs, ON N0H 2T0",
    "report_type": "Saved public-source screening",
    "source_assessment_generated_at": "2026-10-09T22:18:14.484481+00:00",
    "live_assessment": false,
    "overall_project_decision": null,
    "sections": [
      {
        "id": "land",
        "number": "01",
        "kicker": "THE PARCEL",
        "title": "Land & location",
        "status": "Parcel matched",
        "review": false,
        "intro": "The public county parcel matches the civic address and assessment roll number. Its mapped boundary is the common reference for this report.",
        "facts": [
          [
            "Measured parcel area",
            "64.949 acres / 262,838.54 m²"
          ],
          [
            "County recorded acreage",
            "64.897 acres"
          ],
          [
            "Assessment roll number (ARN)",
            "420362000308200"
          ],
          [
            "PIN / title verification",
            "Not independently verified — skipped"
          ],
          [
            "Jurisdiction",
            "Township of Georgian Bluffs, County of Grey"
          ],
          [
            "Boundary type",
            "Public assessment parcel; not a surveyed ownership boundary"
          ]
        ],
        "callout": "Measured area, recorded acreage and historical acreage differ. None is net developable acreage.",
        "method": "County address and ARN matching, visual comparison and GeometryServer geodesic area. Evidence retained from 2–9 October 2026. Geocoder candidates were inconclusive and were not used as parcel boundaries.",
        "sources": [
          0,
          4
        ]
      },
      {
        "id": "soil",
        "number": "02",
        "kicker": "LAND CAPABILITY & TERRAIN",
        "title": "Soil & slope",
        "status": "Exception review",
        "review": true,
        "intro": "Mapped soil units contain CLI Classes 2, 3 and 5. Terrain is mostly below the 15% screening cutoff, with localized steeper cells.",
        "facts": [
          [
            "Mapped CLI classes",
            "2, 3 and 5"
          ],
          [
            "Mixed mapping unit",
            "Class 3 / Class 5, 50% each within the unit"
          ],
          [
            "Mean / median slope",
            "4.57% / 3.95%"
          ],
          [
            "Area above 15% grade",
            "1.351 acres / 2.08% of assessed cells"
          ],
          [
            "Valid slope coverage",
            "100% of parcel raster cells"
          ],
          [
            "Mapped wetlands",
            "3 polygons intersect the parcel"
          ]
        ],
        "callout": "Classes 2 and 3 require a supported exception under the user’s screening rules. Mixed-unit percentages do not identify component locations or parcel acreage shares. Wetland restrictions remain unresolved.",
        "method": "Horn 3×3 gradient on a saved bare-earth DTM, exported at 2 m in EPSG:26917. Cutoff is strictly greater than 15% grade, not degrees. DTM acquisition date is unknown. No soil or wetland exclusions were deducted. Wetland mapping is not field delineation.",
        "sources": [
          1,
          2,
          3
        ]
      },
      {
        "id": "access",
        "number": "03",
        "kicker": "GETTING TO THE SITE",
        "title": "Access & nearby lines",
        "status": "Estimated evidence",
        "review": true,
        "intro": "Historical imagery shows a track entering the clearing from Highway 6. Dated Street View supports a preliminary interpretation of a nearby three-phase circuit.",
        "facts": [
          [
            "Existing track",
            "Visible in 2015 aerial imagery"
          ],
          [
            "Current truck suitability",
            "Unknown"
          ],
          [
            "Legal entrance / highway permission",
            "Not verified"
          ],
          [
            "Estimated nearby phases",
            "3 — visual estimate, not utility confirmation"
          ],
          [
            "Street-level image date",
            "July 2026"
          ],
          [
            "Road-following connection distance",
            "Not calculated; connection endpoints unconfirmed"
          ]
        ],
        "callout": "A visible entrance does not establish legal or truck access. The apparent circuit is across the highway; its serving feeder, crossing requirements and point of connection remain unconfirmed.",
        "method": "2015 county imagery and a retained July 2026 Google Street View observation. Upper crossarm hardware supports an estimated three-phase interpretation. Voltage and feeder identity were not inferred from the image. No fresh imagery was checked for this page.",
        "sources": [
          4
        ]
      },
      {
        "id": "grid",
        "number": "04",
        "kicker": "CANDIDATE CONNECTIONS",
        "title": "Grid capacity",
        "status": "Site result unknown",
        "review": true,
        "intro": "Actual saved calculator trials passed at 2,000 kW for two candidates. Their service relationship to this property has not been confirmed.",
        "facts": [
          [
            "Project scenario",
            "2,000 kW · exporting · inverter-based solar"
          ],
          [
            "Actual site connection",
            "Unknown — serving feeder unconfirmed"
          ]
        ],
        "table": [
          [
            "HEPWORTH DS · F1",
            "Passed",
            "2,700 kW",
            "2,800 kW"
          ],
          [
            "OWEN SOUND TS · M24",
            "Passed",
            "3,000 kW",
            "Not reached"
          ]
        ],
        "callout": "A candidate calculator pass is not site-specific permission and does not reserve capacity. 3,000 kW is the tested ceiling for Owen Sound, not an exact maximum.",
        "method": "Retained Hydro One web calculator trials dated 9 October 2026. Candidates were tested separately. Hepworth has a 100 kW pass/fail bracket. The actual distributor/serving relationship needs confirmation. Grid data has not been refreshed.",
        "sources": [
          5
        ]
      },
      {
        "id": "planning",
        "number": "05",
        "kicker": "LAND USE & PERMISSIONS",
        "title": "Planning & zoning",
        "status": "Further review",
        "review": true,
        "intro": "The parcel has multiple zoning intersections. Electricity-generation wording must be reconciled with environmental restrictions and the proponent’s proposed use.",
        "facts": [
          [
            "Intersecting zoning codes",
            "EP, EP-12, R1, RU, RU-37"
          ],
          [
            "EP-12 overlap",
            "42.236 acres"
          ],
          [
            "RU-37 overlap",
            "22.383 acres"
          ],
          [
            "County map designations",
            "Hazard Lands, Rural, Wetlands"
          ],
          [
            "Private 2 MW ground-mounted solar",
            "Permission not confirmed"
          ],
          [
            "2026 local Official Plan",
            "Adopted; approval/effect and appeals unconfirmed"
          ]
        ],
        "callout": "EP-12 prohibits development/site alteration in the cited exception. RU-37 includes a mapped wetland restriction. General electricity-generation wording does not demonstrate that these restrictions are overridden.",
        "method": "County zoning polygons were intersected with the parcel and measured geodesically. Small EP, RU and R1 overlaps were retained. Saved By-law 2020-020 provisions and the July 2026 adoption notice were reviewed; later amendments and operative approval status were not conclusively exhausted.",
        "sources": [
          6,
          7,
          8
        ]
      }
    ],
    "sources": [
      {
        "name": "Grey County assessment parcels",
        "url": "https://gis.grey.ca/server/rest/services/Public/Service_ParcelLabels/MapServer/0",
        "note": "Address, ARN and parcel geometry · retained 2–9 Oct 2026"
      },
      {
        "name": "Ontario agricultural soil mapping",
        "url": "https://ws.lioservices.lrc.gov.on.ca/arcgis4/rest/services/AIA/AIA_Map/MapServer/29",
        "note": "CLI mapping units and composition · retained Oct 2026"
      },
      {
        "name": "Ontario wetlands mapping",
        "url": "https://ws.lioservices.lrc.gov.on.ca/arcgis2/rest/services/LIO_OPEN_DATA/LIO_Open01/MapServer/15",
        "note": "Mapped intersections; boundaries and regulatory constraints require review"
      },
      {
        "name": "Ontario lidar-derived DTM",
        "url": "https://ws.geoservices.lrc.gov.on.ca/arcgis5/rest/services/Elevation/Ontario_DTM_LidarDerived/ImageServer",
        "note": "Saved 2 m export · retrieved 2 Oct 2026 · acquisition date unknown"
      },
      {
        "name": "Grey County 2015 aerial imagery",
        "url": "https://gis.grey.ca/server/rest/services/Public/AirPhotos2015/ImageServer",
        "note": "Historical imagery, not present-day site confirmation"
      },
      {
        "name": "Hydro One capacity calculator",
        "url": "https://www.hydroone.com/businessservices_/generators_/Pages/stationcapacitycalculator.aspx",
        "note": "Saved actual candidate trials · 9 Oct 2026 · no capacity reservation"
      },
      {
        "name": "Grey County Georgian Bluffs zoning",
        "url": "https://gis.grey.ca/server/rest/services/Public/Service_GreyCountyZoning/MapServer/1",
        "note": "Parcel intersections · not a determination of permitted use"
      },
      {
        "name": "Georgian Bluffs planning notices",
        "url": "https://www.georgianbluffs.ca/build-and-invest/land-use-planning/public-notices/",
        "note": "Saved 2026 plan adoption notice; approval/effect unconfirmed"
      },
      {
        "name": "Georgian Bluffs zoning by-law",
        "url": "https://www.georgianbluffs.ca/build-and-invest/land-use-planning/zoning-by-law/",
        "note": "By-law 2020-020 and cited exceptions · later amendments not exhausted"
      }
    ]
  }
};
