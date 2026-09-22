import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, Point, Polygon

from process_incra import fix_geometry, normalize_fields


class TestFixGeometry:
    def test_converts_polygon_z_to_2d_multipolygon(self):
        poly = Polygon([(0, 0, 5), (1, 0, 5), (1, 1, 5), (0, 1, 5)])
        result = fix_geometry(poly)
        assert result.geom_type == "MultiPolygon"
        assert not result.has_z

    def test_repairs_invalid_polygon(self):
        bowtie = Polygon([(0, 0), (1, 1), (1, 0), (0, 1)])
        result = fix_geometry(bowtie)
        assert result is not None
        assert result.is_valid

    def test_rejects_non_polygon(self):
        assert fix_geometry(LineString([(0, 0), (1, 1)])) is None
        assert fix_geometry(Point(0, 0)) is None
        assert fix_geometry(None) is None


class TestNormalizeFields:
    def test_keeps_target_fields_truncates_text_and_parses_dates(self):
        gdf = gpd.GeoDataFrame({
            "num_proces": ["x" * 100],
            "data_certi": [pd.Timestamp("2026-02-06")],
            "uf_municip": ["  PB  "],
            "campo_extra": ["descartado"],
        }, geometry=[Polygon([(0, 0), (1, 0), (1, 1)])], crs=4326)

        result = normalize_fields(gdf, "snci")

        assert "campo_extra" not in result.columns
        assert len(result.loc[0, "num_proces"]) == 70
        assert result.loc[0, "uf_municip"] == "PB"
        assert result.loc[0, "data_certi"] == pd.Timestamp("2026-02-06")  # 6 de fevereiro, não 2 de junho
