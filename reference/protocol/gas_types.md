# Gas Type Reference

Quick reference for Gen II WireFree gas type codes.

## Gas Type Codes

| Code | Gas Name | Chemical Formula | Units | Typical Range | Alarm Levels |
|------|----------|------------------|-------|---------------|--------------|
| 0x00 | H2S | Hydrogen Sulfide | ppm | 0-100 | TWA: 10, STEL: 15 |
| 0x01 | CO | Carbon Monoxide | ppm | 0-1000 | TWA: 35, STEL: 200 |
| 0x02 | O2 | Oxygen | % | 0-25 | Low: 19.5, High: 23.5 |
| 0x03 | LEL | Combustible Gas | % LEL | 0-100 | 10%, 20% |
| 0x04 | SO2 | Sulfur Dioxide | ppm | 0-20 | TWA: 2, STEL: 5 |
| 0x05 | NO2 | Nitrogen Dioxide | ppm | 0-20 | TWA: 3, STEL: 5 |
| 0x06 | Cl2 | Chlorine | ppm | 0-10 | TWA: 0.5, STEL: 1 |
| 0x07 | NH3 | Ammonia | ppm | 0-100 | TWA: 25, STEL: 35 |
| 0x08 | VOC | Volatile Organic Compound | ppm | 0-2000 | Varies by compound |
| 0x09 | HCN | Hydrogen Cyanide | ppm | 0-30 | TWA: 4.7, STEL: 10 |
| 0x0A | PH3 | Phosphine | ppm | 0-5 | TWA: 0.3, STEL: 1 |
| 0x0B | HCl | Hydrogen Chloride | ppm | 0-10 | Ceiling: 5 |
| 0x0C | NO | Nitric Oxide | ppm | 0-250 | TWA: 25 |
| 0x0D | CO2 | Carbon Dioxide | % | 0-5 | TWA: 0.5% (5000 ppm) |
| 0x0E | IR HC | Infrared Hydrocarbon | % LEL | 0-100 | 10%, 20% |
| 0x0F | ClO2 | Chlorine Dioxide | ppm | 0-1 | TWA: 0.1, STEL: 0.3 |

## Usage in Code

### Python

```python
GAS_TYPES = {
    0x00: 'H2S',
    0x01: 'CO',
    0x02: 'O2',
    0x03: 'LEL',
    0x04: 'SO2',
    0x05: 'NO2',
    0x06: 'Cl2',
    0x07: 'NH3',
    0x08: 'VOC',
    0x09: 'HCN',
    0x0A: 'PH3',
    0x0B: 'HCl',
    0x0C: 'NO',
    0x0D: 'CO2',
    0x0E: 'IR HC',
    0x0F: 'ClO2'
}

# Decode gas type from packet
gas_code = packet[9] & 0x7F  # Mask bit 7
gas_name = GAS_TYPES.get(gas_code, 'Unknown')
```

### Units by Gas Type

```python
def get_units(gas_code):
    """Get measurement units for gas type."""
    if gas_code in [0x02, 0x03, 0x0D, 0x0E]:  # O2, LEL, CO2, IR HC
        return '%'
    else:
        return 'ppm'
```

## Active Sensors in System

Based on current deployment (Network 15):

| Channel | Gas Type | Code | Reading | Battery | Notes |
|---------|----------|------|---------|---------|-------|
| Ch002 | H2S | 0x00 | 0.0 ppm | 21.0V | Line powered |
| Ch003 | H2S | 0x00 | 0.0 ppm | 3.4V | Battery low |
| Ch005 | CO | 0x01 | 0.0 ppm | 3.6V | Normal |
| Ch010 | H2S | 0x00 | 0.0 ppm | 11.0V | Good |
| Ch012 | LEL (NH3) | 0x03 | 0.0% | 11.0V | Combustible |
| Ch020 | VOC (Cl2) | 0x08 | 0.0 ppm | 3.9V | Chlorine detection |
| Ch022 | LEL (NH3) | 0x03 | 0.0% | 3.9V | Ammonia as LEL |
| Ch023 | LEL (NH3) | 0x03 | 0.0% | 3.9V | Ammonia as LEL |
| Ch033 | H2S | 0x00 | 0.0 ppm | 22.0V | Line powered |
| Ch255 | O2 | 0x02 | 20.9% | 23.0V | Validated ✅ |

## Gas Detection Technology

### Sensor Types (Mode Byte)

| Type | Name | Best For | Gases |
|------|------|----------|-------|
| 0 | Electrochemical (EC) | Toxic gases | H2S, CO, SO2, NO2, Cl2, NH3 |
| 1 | Infrared (IR) | Combustibles | CH4, propane, CO2 |
| 2 | Catalytic Bead (CB) | Combustibles | LEL, hydrocarbons |
| 3 | Metal Oxide (MOS) | VOCs | General VOCs |
| 4 | Photoionization (PID) | VOCs | Specific VOCs |

### Typical Sensor Lifespan

| Technology | Expected Life | Factors |
|------------|---------------|---------|
| EC | 2-3 years | Target gas exposure, temperature |
| IR | 5+ years | Stable, long-lasting |
| CB | 3-5 years | Poisons (silicones, sulfur) |
| MOS | 2-3 years | High humidity, contaminants |
| PID | 2-3 years | UV lamp life, contamination |

## Safety Information

### OSHA PELs (Permissible Exposure Limits)

- **TWA** (Time Weighted Average): 8-hour exposure limit
- **STEL** (Short Term Exposure Limit): 15-minute exposure limit
- **Ceiling**: Never exceed limit

### Critical Gas Hazards

**H2S (Hydrogen Sulfide)**:
- 10 ppm: TWA limit, noticeable odor
- 50 ppm: Eye irritation
- 100 ppm: Olfactory fatigue (can't smell)
- 500 ppm: Life threatening
- 700 ppm: Immediate death

**CO (Carbon Monoxide)**:
- 35 ppm: TWA limit
- 200 ppm: STEL, headache
- 400 ppm: Life threatening after 3 hours
- 800 ppm: Unconsciousness, death

**O2 (Oxygen)**:
- < 19.5%: OSHA deficient, danger
- 19.5-23.5%: Normal range
- > 23.5%: Fire/explosion risk

**LEL (Combustible)**:
- 10% LEL: Alarm setpoint
- 20% LEL: High alarm
- 100% LEL: Lower explosive limit
- At 100% LEL, atmosphere can ignite

## Calibration Gas Standards

### Common Calibration Gases

| Gas | Cal Concentration | Balance |
|-----|-------------------|---------|
| H2S | 25 ppm | Nitrogen |
| CO | 100 ppm | Nitrogen |
| O2 | 20.9% | Nitrogen |
| LEL (CH4) | 50% LEL (2.5% CH4) | Air |
| SO2 | 5 ppm | Nitrogen |
| NO2 | 5 ppm | Air |
| Cl2 | 2 ppm | Nitrogen |
| NH3 | 50 ppm | Nitrogen |

## Troubleshooting

### Reading Issues by Gas Type

**O2 Sensors**:
- Low reading indoors: Normal (slightly below 20.9%)
- High reading: Check for leaks, sensor failure
- Expected: 20.5-20.9% in normal air

**LEL Sensors**:
- Non-zero in clean air: Check for contamination
- Negative reading: Needs calibration
- Erratic: Check for silicone contamination

**Toxic Sensors (H2S, CO, etc.)**:
- Slow response: Sensor aging, replace
- Negative reading: Zero drift, recalibrate
- Won't zero: Sensor exhausted, replace

### Battery Voltage by Power Source

| Voltage Range | Power Source | Action |
|---------------|--------------|--------|
| 2.0-2.5V | Battery (critical low) | Replace immediately |
| 2.5-3.5V | Battery (low) | Replace soon |
| 3.5-4.0V | Battery (good) | Monitor |
| 10-12V | Solar/rechargeable | Check charging |
| 20-24V | Line powered | Normal |

## References

- OSHA 29 CFR 1910.146 (Permit-Required Confined Spaces)
- OSHA 29 CFR 1910.1000 (Air Contaminants)
- ANSI/ISA-12.13.01 (Combustible Gas Detectors)
- IEC 60079-29-1 (Gas Detectors - Performance Requirements)
- Manufacturer calibration procedures

## Notes

- All alarm levels are typical defaults. Site-specific levels may vary.
- TWA/STEL values are US OSHA standards. International standards may differ.
- LEL calculations assume methane. Adjust for other combustibles.
- O2 readings affected by altitude (lower at higher elevation).
