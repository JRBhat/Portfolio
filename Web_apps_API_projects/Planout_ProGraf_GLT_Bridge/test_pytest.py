import RoomDefinitions, PlanoutImport_MSSQL_adjusted as PlanoutImport, sendJSON
import pytest


def test_true():
    assert True

def test_false():
    assert False != True

def test_roomsReadable():
    assert 'Luna1' in RoomDefinitions.RoomDefinitions().roomdict
    assert {'GLTNAME' : 'LUNA U 1', 'PLANOUTNAME' : 'Luna R1 (-255)', 'RES_ID' : 51, 'CAPABILITIES' : 'HC' } == RoomDefinitions.RoomDefinitions().roomdict['Luna1']

def test_error():
    with pytest.raises(LookupError) as e_info:
        result = RoomDefinitions.RoomDefinitions().translateCanonicalToGLT("ERRORMEPLZ")


@pytest.mark.category_database_access
@pytest.fixture
def nested_fixture(example_fixture):
    return example_fixture+1

@pytest.fixture
def example_fixture():
    return 1

def test_fixtures(example_fixture):
    assert example_fixture == 1

def test_nested_fixtures(nested_fixture):
    assert nested_fixture == 2


@pytest.mark.parametrize("parameter1, parameter2", [
    (1, 2),
    (-1, 0),
    (999, 1000)
    ])

def test_add1(parameter1, parameter2):
    assert parameter1+1 == parameter2



def test_planout_db_mock(monkeypatch):
    import datetime

    # Application of the monkeypatch to replace Path.home
    # with the behavior of mockreturn defined above.
    monkeypatch.setattr(PlanoutImport.PlanoutImport, "fetch", PlanoutImport.PlanoutImport.fetchDummyData, raising=True)

    # Calling getssh() will use mockreturn in place of Path.home
    # for this test with the monkeypatch.
    x = PlanoutImport.PlanoutImport().fetch()
   
    todaystart = datetime.datetime(year=datetime.datetime.today().year, month=datetime.datetime.today().month, day=datetime.datetime.today().day, hour=8, minute=30, second=0)
    todaystop = datetime.datetime(year=datetime.datetime.today().year, month=datetime.datetime.today().month, day=datetime.datetime.today().day, hour=17, minute=00, second=0)
    todayintwominutes = datetime.datetime.today() + datetime.timedelta(minutes=2)
    assert x == [{'RESSOURCE': 'Luna R9 Fotoraum (-72)', 'TEMPFEUCHTE': None, 'MIN(STARTDATUM)': todaystart, 'MAX(ENDEDATUM)': todaystop, 'COUNT(RESSOURCE)': 1, 'RES_ID': 88, 'TEMPERATUR': '22.0', 'FEUCHTE': '50.0'}]


@pytest.fixture(autouse=True)
def mock_glt_send(monkeypatch):
    monkeypatch.setattr(sendJSON.sendJSON, "sendToGLT", lambda x: True)


def test_send_to_glt():
    assert True == sendJSON.sendJSON.sendToGLT(list())


