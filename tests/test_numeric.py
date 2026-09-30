import math
import pytest
from make_font_with_ai.numeric import font_unit_round

@pytest.mark.parametrize('half',[-1000.5,-2.5,-1.5,-.5,.5,1.5,2.5,1000.5])
def test_half_unit_is_cpu_approach_independent(half):
    assert font_unit_round(math.nextafter(half,-math.inf))==round(half)
    assert font_unit_round(math.nextafter(half,math.inf))==round(half)
    assert font_unit_round(half)==round(half)

@pytest.mark.parametrize('value,expected',[(.4999999,0),(.5000001,1),(1.4999999,1),(1.5000001,2),(-.4999999,0),(-.5000001,-1)])
def test_real_subunit_difference_is_not_erased(value,expected):
    assert font_unit_round(value)==expected

@pytest.mark.parametrize('value',[math.nan,math.inf,-math.inf])
def test_nonfinite_coordinates_rejected(value):
    with pytest.raises(ValueError):font_unit_round(value)
