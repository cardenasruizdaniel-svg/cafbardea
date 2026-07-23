from sqlalchemy import inspect, create_engine

eng = create_engine('sqlite:///./cafbardla.db')
insp = inspect(eng)
cols = insp.get_columns('detalle_ventas')
print('Columnas de detalle_ventas:')
for c in cols:
    print(f'  - {c["name"]}: {c["type"]}')
