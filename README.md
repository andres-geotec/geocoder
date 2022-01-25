# Geocoder

# Requerimientos:
- Python 3.9
- Archivo original de entrada en .xlsx
- El archivo original no deve contener las columnas "georef", "direccion_concat", "lat", "lng"

# Istrucciones

### Para iniciar

- Crear entorno virtual
`virtualenv env -p python3.8`

- Activar entorno virtual
`source env/bin/activate`

- Instalar modulos necesarios
`pip install -r requirements.txt`


### Para ejecutar

- Adecuar variables del 
- Correr script
`python georef.py <archivo_original> <id>`

Dónde 
  - archivo_original: es el archivo que se necesita geocodificar (debe ubicarse en la carpeta data_original)
  - id: es el identificardor único del archivo

Ejemplo
`python georef.py concentrado_prueba1.xlsx id`



### Al finalizar

- Desactivar entorno virtual
`deactivate`