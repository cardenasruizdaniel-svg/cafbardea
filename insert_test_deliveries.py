#!/usr/bin/env python
"""Insert test delivery records for testing delivery panels"""

from datetime import datetime, date
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database connection  
DATABASE_URL = "sqlite:///./cafbardla.db"
engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)
session = Session()

try:
    # Insert test records into detalle_ventas with estado_cocina = 'entregado'
    sql = text("""
    INSERT INTO detalle_ventas (
        venta_id, producto_id, cantidad, precio, costo_unitario,
        estado_cocina, creado_en, estado_actualizado_en, nota
    ) VALUES 
    (:venta_id, :producto_id, :cantidad, :precio, :costo_unitario,
     :estado_cocina, :creado_en, :estado_actualizado_en, :nota)
    """)
    
    now = datetime.now()
    
    records = [
        {
            'venta_id': 1,
            'producto_id': 1,
            'cantidad': 2,
            'precio': 5.50,
            'costo_unitario': 1.50,
            'estado_cocina': 'entregado',
            'creado_en': now,
            'estado_actualizado_en': now,
            'nota': 'Café con leche'
        },
        {
            'venta_id': 1,
            'producto_id': 2,
            'cantidad': 1,
            'precio': 3.50,
            'costo_unitario': 1.00,
            'estado_cocina': 'entregado',
            'creado_en': now,
            'estado_actualizado_en': now,
            'nota': 'Croissant'
        },
        {
            'venta_id': 2,
            'producto_id': 3,
            'cantidad': 3,
            'precio': 4.00,
            'costo_unitario': 0.80,
            'estado_cocina': 'entregado',
            'creado_en': now,
            'estado_actualizado_en': now,
            'nota': 'Jugo fresco'
        }
    ]
    
    for record in records:
        session.execute(sql, record)
        print(f"✓ Inserted: Venta {record['venta_id']}, Producto {record['producto_id']}, Qty {record['cantidad']}")
    
    session.commit()
    print("\n✅ Test delivery records inserted successfully!")
    print("   The delivery panels should now be visible in /mesas and /mobile")
    
except Exception as e:
    session.rollback()
    print(f"❌ Error: {e}")
finally:
    session.close()
