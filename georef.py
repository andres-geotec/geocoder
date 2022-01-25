

import os
import sys
import json
import pandas as pd
from math import isnan
import geopandas as gpd
import fuzzywuzzy.fuzz as fuzz
from unidecode import unidecode
from geocoder import arcgis as geocode

# nombre del archivo original (debe ubicarse en la carpeta data_original)
ARCHIVO_ORIGINAL = sys.argv[1]

# identificador de las filas del dataset
ID_COLUMN = sys.argv[2]

print("ejcutando {}...\n".format(sys.argv[0]))


# Versipon de python en la que se hace la ejecuión (lectura automática)
py_version = int(sys.version[:1])

#++++++++++++++++++++  ++++++++++++++++++++
#valida que una carpeta exista
def checkFolder(_folder):
  if os.path.isdir(_folder) == False:
    os.mkdir(_folder)
    print(f'Se ha creao la carpeta {_folder}')

# Devuelve los valores de un JSON
def getJSON(_file):
    _f = open(_file, 'r')
    _data = json.load(_f)
    _f.close()
    return _data

# Obtener abreviatutras
acronyms = getJSON(os.path.join("data_auxiliar", "abreviaturas.json"))
DIC_ADDRESS_COLUMNAS = getJSON("relacion_columnas.json")
#++++++++++++++++++++  ++++++++++++++++++++

#++++++++++++++++++++ Homologación de dirección ++++++++++++++++++++
def validateStr(_val):
    return _val if type(_val) is str else ('' if isnan(_val) else str(_val))

# Remplaza las letras ñ si la versión de python es mayor a 2
def replace_n(_txt):
    if py_version < 3: return _txt
    return _txt.replace('&', 'Ñ').replace('Ñ ', '& ').upper().strip()

# Expande avrebiaturas
def expandAcronym(_all_text, _acronym, _new_text):
    return _all_text.upper().strip().replace(
        '{} '.format(unidecode(_acronym)), '{} '.format(unidecode(_new_text))).replace(
        '{}. '.format(unidecode(_acronym)), '{} '.format(unidecode(_new_text))).replace(
        '{}.'.format(unidecode(_acronym)), '{} '.format(unidecode(_new_text)))

# Valida la escritura de calles
def validateStreet(_street):
    if _street is None: return ''
    for i in acronyms['streets'].keys():
        _street = expandAcronym(_street, i, acronyms['streets'].get(i))
    return replace_n(_street)

# Valida numeros exteriores
def validateNumExt(_num):
    ops = ['SN','S.N','S N','SN.','S  N','S.N.','S. N.','S   N']
    if _num.upper().strip() in ops: _num = 'S/N'
    #for i in ops: _num = _num.replace(i, 'S/N')
    return _num.upper().strip()

# Valida nombres de colonias
def validateColony(_colony):
    if _colony is None: return ''
    for i in acronyms['colonies'].keys():
        _colony = expandAcronym(_colony, i, acronyms['colonies'].get(i))
    return replace_n(_colony)

# Construye la nomenclatura de la dirección
def concateAddress(_street, _num, _col, _mun, _ent, _cp):
    # Validar Calle
    address = validateStreet(validateStr(_street))
    # Validar Número exterior
    address += " " + validateNumExt(validateStr(_num))
    # Validar Colonia
    address = address.strip() + ", " + validateColony(validateStr(_col))
    address += ", " + unidecode(validateStr(_mun))
    address += ", " + unidecode(validateStr(_ent))
    #address += ", " + unidecode(country.decode('utf-8') if py_version < 3 else country)
    # Validar Código postal
    address += ", " + validateStr(_cp).zfill(5)
    return address.upper().strip()

# Añade la dirección a la tabla
def addAddress(_df):
    _df['address'] = _df.apply(
        lambda i: concateAddress(
            i[DIC_ADDRESS_COLUMNAS.get("CALLE")],
            i[DIC_ADDRESS_COLUMNAS.get("N_EXT")],
            i[DIC_ADDRESS_COLUMNAS.get("COLONIA")],
            i[DIC_ADDRESS_COLUMNAS.get("MUN")],
            i[DIC_ADDRESS_COLUMNAS.get("ENT")],
            i[DIC_ADDRESS_COLUMNAS.get("CP")]), axis=1)
    return _df
#++++++++++++++++++++ Homologación de dirección ++++++++++++++++++++

#++++++++++++++++++++ Validaciones de texto ++++++++++++++++++++
# Devuelve la evaluación de coincidencia entre textos
def compareText(txt1, txt2):
    z = fuzz.ratio(unidecode(txt1).lower(), unidecode(txt2).lower())
    #z = fuzz.ratio(unidecode.unidecode(str(txt1).lower()), unidecode.unidecode(str(txt2).lower()))
    #print(f'- {z} => {original}')
    return z
# Compara el geocoder con la dirección y devuelve la coincidencia más alta
def compareAddresss(new_points, address):
    new_points['acuracy'] = new_points['address'].apply(lambda x: compareText(x, address))
    return new_points[new_points['acuracy'] == new_points['acuracy'].max()].copy()
#++++++++++++++++++++ Validaciones de texto ++++++++++++++++++++

#++++++++++++++++++++ Validaciones espaciales ++++++++++++++++++++
# Devuelve las georeferencias a partir de una dirección
def georef(_addres):
    _geocode = geocode(_addres, maxRows=5)
    _df = pd.DataFrame({
        'address': [i.address for i in _geocode],
        'lat': [i.latlng[0] for i in _geocode],
        'lng': [i.latlng[1] for i in _geocode]})
    #return gpd.GeoDataFrame(_df, geometry=gpd.points_from_xy(
    #    _df.lng, _df.lat), crs="EPSG:4326")
    return _df
#++++++++++++++++++++ Validaciones espaciales ++++++++++++++++++++


print("Leyendo {}...".format(ARCHIVO_ORIGINAL))
contenido_original = pd.read_excel(
    os.path.join("data_original", ARCHIVO_ORIGINAL),
    dtype={val: str for val in DIC_ADDRESS_COLUMNAS.values()}
).set_index(ID_COLUMN)
#print(contenido_original[[val for val in DIC_ADDRESS_COLUMNAS.values()]].head())

contenido_original = addAddress(contenido_original)
georeferenciados = pd.DataFrame()
for i, row in contenido_original.copy().iterrows():
    print("\n\n[{}] > {}".format(i, row['address']))
    try:
        # Obtener geometria georeferenciada
        new_points = georef(row['address'])
        print('> {} opciones'.format(len(new_points)))

        # Evaluar por dirección
        match_text = compareAddresss(new_points, row['address'])
        print('{} (tiene la mayor coincidencia)'.format(
            unidecode(match_text['address'].values[0])))

        match_text[ID_COLUMN] = [i]

        #if georeferenciados is None:
        georeferenciados = pd.concat([georeferenciados, match_text.copy().set_index(ID_COLUMN)])

    except:
        print('NO SE PUDO GEOREFERENCIAR! {}'.format(i))
        continue
print('\n\t\t***Proceso terminado')

#print(georeferenciados.head())
tode = contenido_original.rename(columns={"address": "direccion_concat"}).merge(
    georeferenciados.rename(columns={"address": "georef"}),
    on=ID_COLUMN,
    how='outer')
# print(tode.head())

layer = gpd.GeoDataFrame(tode, geometry=gpd.points_from_xy(
    tode.lng, tode.lat), crs="EPSG:4326")
print(layer.head())

checkFolder("data_procesada")
layer.to_file(
    os.path.join("data_procesada", "{}_georeferenciados.gpkg".format(
        ARCHIVO_ORIGINAL.split('.')[0]
    )),
    driver='GPKG',
    layer='georeferenciados')  
