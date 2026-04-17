-- ============================================================
--  PCB Builder - Seed Data
--  Sample data for development & testing
-- ============================================================

-- Sample fabricators
INSERT INTO fabricators (id, name, country, website_url, capabilities, supported_types, is_active) VALUES
(
    gen_random_uuid(),
    'PCB Power',
    'India',
    'https://pcbpower.in',
    '{
        "min_layers": 1, "max_layers": 8,
        "min_trace_mm": 0.1, "min_space_mm": 0.1,
        "min_via_mm": 0.2,
        "materials": ["FR4", "Rogers", "Aluminum"],
        "surface_finish": ["HASL", "ENIG", "OSP", "Hard Gold"],
        "copper_weight": ["0.5oz", "1oz", "2oz", "3oz"],
        "max_board_size_mm": [600, 500],
        "min_board_thickness_mm": 0.4,
        "max_board_thickness_mm": 3.2
    }'::jsonb,
    ARRAY['rigid', 'flex', 'rigid-flex', 'hdi'],
    true
),
(
    gen_random_uuid(),
    'JLCPCB',
    'China',
    'https://jlcpcb.com',
    '{
        "min_layers": 1, "max_layers": 14,
        "min_trace_mm": 0.09, "min_space_mm": 0.09,
        "min_via_mm": 0.15,
        "materials": ["FR4", "Aluminum", "Rogers"],
        "surface_finish": ["HASL", "HASL Lead-Free", "ENIG"],
        "copper_weight": ["1oz", "2oz"],
        "max_board_size_mm": [500, 400],
        "min_board_thickness_mm": 0.4,
        "max_board_thickness_mm": 2.4
    }'::jsonb,
    ARRAY['rigid', 'flex', 'rigid-flex'],
    true
),
(
    gen_random_uuid(),
    'Rush PCB',
    'India',
    'https://rushpcb.com',
    '{
        "min_layers": 1, "max_layers": 16,
        "min_trace_mm": 0.075, "min_space_mm": 0.075,
        "min_via_mm": 0.15,
        "materials": ["FR4", "Rogers", "Polyimide", "Aluminum"],
        "surface_finish": ["HASL", "ENIG", "OSP", "Immersion Silver", "Immersion Tin"],
        "copper_weight": ["0.5oz", "1oz", "2oz", "3oz", "4oz"],
        "max_board_size_mm": [800, 600],
        "min_board_thickness_mm": 0.2,
        "max_board_thickness_mm": 6.0
    }'::jsonb,
    ARRAY['rigid', 'flex', 'rigid-flex', 'hdi', 'heavy-copper'],
    true
);

-- Sample components (common parts)
INSERT INTO components (id, mpn, name, description, category, subcategory, manufacturer, package_type, pin_count, datasheet_data) VALUES
(
    gen_random_uuid(),
    'LM7805CT',
    'LM7805 Voltage Regulator',
    '5V 1A Fixed Positive Voltage Regulator',
    'Power Management',
    'Linear Regulators',
    'Texas Instruments',
    'TO-220-3',
    3,
    '{"input_voltage_range": [7, 35], "output_voltage": 5, "output_current_max_a": 1.5, "dropout_voltage": 2, "quiescent_current_ma": 5}'::jsonb
),
(
    gen_random_uuid(),
    'ATmega328P-PU',
    'ATmega328P Microcontroller',
    '8-bit AVR MCU with 32KB Flash, 2KB SRAM, 1KB EEPROM',
    'Microcontrollers',
    '8-bit MCU',
    'Microchip',
    'DIP-28',
    28,
    '{"flash_kb": 32, "sram_kb": 2, "eeprom_kb": 1, "clock_max_mhz": 20, "gpio_count": 23, "adc_channels": 8, "uart": 1, "spi": 1, "i2c": 1}'::jsonb
),
(
    gen_random_uuid(),
    'ESP32-WROOM-32E',
    'ESP32 Wi-Fi+BLE Module',
    'Dual-core 240MHz Wi-Fi + Bluetooth 4.2 + BLE module',
    'Wireless Modules',
    'Wi-Fi + Bluetooth',
    'Espressif',
    'Module-38',
    38,
    '{"cpu_cores": 2, "clock_mhz": 240, "flash_mb": 4, "sram_kb": 520, "wifi": "802.11 b/g/n", "bluetooth": "4.2+BLE", "gpio_count": 34, "adc_channels": 18}'::jsonb
),
(
    gen_random_uuid(),
    'STM32F411CEU6',
    'STM32F411 ARM Cortex-M4 MCU',
    'High-performance ARM Cortex-M4 MCU with FPU, 512KB Flash',
    'Microcontrollers',
    '32-bit ARM',
    'STMicroelectronics',
    'UFQFPN-48',
    48,
    '{"cpu": "ARM Cortex-M4F", "clock_mhz": 100, "flash_kb": 512, "sram_kb": 128, "gpio_count": 36, "adc_channels": 10, "uart": 3, "spi": 5, "i2c": 3, "usb": 1}'::jsonb
),
(
    gen_random_uuid(),
    'AMS1117-3.3',
    'AMS1117-3.3 LDO Regulator',
    '3.3V 1A Low Dropout Voltage Regulator',
    'Power Management',
    'LDO Regulators',
    'Advanced Monolithic Systems',
    'SOT-223',
    3,
    '{"output_voltage": 3.3, "output_current_max_a": 1.0, "dropout_voltage": 1.3, "input_voltage_max": 15, "quiescent_current_ma": 5}'::jsonb
),
(
    gen_random_uuid(),
    'USB-C-16P',
    'USB Type-C 16-Pin Connector',
    'USB Type-C receptacle, 16-pin, SMD, mid-mount',
    'Connectors',
    'USB',
    'Generic',
    'SMD',
    16,
    '{"type": "USB-C", "pins": 16, "current_rating_a": 5, "voltage_max_v": 20, "data_rate": "USB 2.0"}'::jsonb
);
