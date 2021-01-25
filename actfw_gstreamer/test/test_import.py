from nose2.tools import params


@params(
    # {'from': 'actfw_gstreamer.foo', 'import': 'Bar'},
)
def test_import_actfw_gstreamer(param):
    exec(f'''from {param['from']} import {param['import']}''')
