import pytest
from read_map import MapParser, ParseError
from glob import glob

INVALID_MAPS: list[str] = sorted(glob("invalid_maps/*.txt"))


@pytest.mark.parametrize("map_path", INVALID_MAPS)
def test_invalid_maps(map_path: str) -> None:
    """Check that parsing an invalid map raises a ParseError.

    Args:
        Map_path: Path to one of the invalid map files in invalid_maps/.
    """
    parser = MapParser(map_path)
    with pytest.raises(ParseError):
        parser.check_map()
