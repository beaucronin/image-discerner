# Target Definitions

The discernment system identifies and describes commercial and infrastructure entities in user-submitted images. Each image can contain multiple entities, though it is likely that a typical image will contain at most one.

Each entity will be categorized, its identifiers recognized and specified, and its operator (if any) provided.

## Categories and subcategories

- commercial_vehicle
  - van
  - step_van
  - panel_truck
  - tractor_trailer
  - propeller_aircraft
  - jet_aircraft
- cargo_container

## Identifiers
Zero or more of

- license_plate
  - jurisdiction
  - number
- fleet_id
- container_id
- tail_id
- other_id

## Operators
Up to one of

- fedex
- ups
- usps
- dhl
- amazon
- (many others)

## Examples

{
    "type": "commercial_vehicle:van",
    "operator": "usps",
    "identifiers": [
        "license_plate:california:4FGG123",
        "fleet:abc123"
    ]
}

{
    "type": "cargo_container",
    "operator": "Matson",
    "identifiers: [
        "container_id:MATU 260034 0"
    ],
    "properties": {
        "size_code": "45G1"
    }
}

{
    "type": "electrical_transformer:pole_top",
    "properties": {
        "rating_kva": 50
    }
}