from typing import List
from app.models.schemas import ContractTemplate


BASIC_USER_EVENTS = """contract_version: "1.0"
domain: "user-analytics"
description: "Basic user events contract"
schema:
  user_id:
    type: string
    required: true
    pattern: "^usr_\\d+$"
    description: "Unique user identifier"
  email:
    type: string
    format: email
    required: true
    description: "User email address"
  age:
    type: integer
    required: false
    min: 13
    max: 120
    description: "User age"
  timestamp:
    type: timestamp
    required: true
    description: "Event timestamp"
quality_rules:
  freshness:
    max_latency_hours: 1
  completeness:
    min_row_count: 100
    max_null_percentage: 5
"""

ECOMMERCE_ORDERS = """contract_version: "1.0"
domain: "e-commerce"
description: "E-commerce order events"
schema:
  order_id:
    type: string
    pattern: "^ord_[a-zA-Z0-9]+$"
    required: true
    description: "Unique order identifier"
  customer_id:
    type: string
    required: true
    description: "Customer identifier"
  total_amount:
    type: float
    min: 0
    required: true
    description: "Total order amount"
  items:
    type: array
    required: true
    description: "Order line items"
    items:
      type: object
      properties:
        product_id:
          type: string
          required: true
        quantity:
          type: integer
          min: 1
          required: true
        price:
          type: float
          min: 0
          required: true
  order_date:
    type: timestamp
    required: true
quality_rules:
  freshness:
    max_latency_hours: 24
  completeness:
    min_row_count: 1
"""

IOT_SENSOR_DATA = """contract_version: "1.0"
domain: "iot"
description: "IoT sensor readings"
schema:
  device_id:
    type: string
    required: true
    description: "Device identifier"
  sensor_type:
    type: string
    enum: ["temperature", "humidity", "pressure"]
    required: true
    description: "Type of sensor"
  value:
    type: float
    required: true
    description: "Sensor reading value"
  unit:
    type: string
    required: true
    description: "Unit of measurement"
  timestamp:
    type: timestamp
    required: true
quality_rules:
  freshness:
    max_latency_hours: 1
  completeness:
    min_row_count: 10
"""


def get_all_templates() -> List[ContractTemplate]:
    return [
        ContractTemplate(
            name="basic-user-events",
            description="Basic user analytics events with user ID and email",
            domain="user-analytics",
            yaml_content=BASIC_USER_EVENTS
        ),
        ContractTemplate(
            name="ecommerce-orders",
            description="E-commerce order events with line items",
            domain="e-commerce",
            yaml_content=ECOMMERCE_ORDERS
        ),
        ContractTemplate(
            name="iot-sensor-data",
            description="IoT sensor readings with device tracking",
            domain="iot",
            yaml_content=IOT_SENSOR_DATA
        )
    ]


def get_template_by_name(name: str) -> ContractTemplate:
    templates = {t.name: t for t in get_all_templates()}
    return templates.get(name)