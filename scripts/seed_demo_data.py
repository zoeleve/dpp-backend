import requests
import json
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

# Configuration
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
LOGIN_URL = f"{BASE_URL}/auth/login"
REGISTER_URL = f"{BASE_URL}/users/"
API_URL = f"{BASE_URL}/dpp/json/"
SEARCH_URL = f"{BASE_URL}/dpp/json/search"

# Credentials
USERNAME = os.getenv("API_USERNAME", "zoe")
PASSWORD = os.getenv("API_PASSWORD", "test")
EMAIL = os.getenv("API_EMAIL", "zoe@example.com")

def create_user():
    logging.info(f"👤 Attempting to create user '{USERNAME}'...")
    payload = {
        "username": USERNAME,
        "password": PASSWORD,
        "email": EMAIL,
        "role": "admin"
    }
    try:
        response = requests.post(REGISTER_URL, data=payload)
        if response.status_code in [200, 201]:
            logging.info("✅ User created successfully!")
        elif response.status_code == 400 and "Email already registered" in response.text:
            logging.info("ℹ️ User already exists (Email registered).")
        elif response.status_code == 400 and "Username already taken" in response.text:
             logging.info("ℹ️ User already exists (Username taken).")
        else:
            logging.warning(f"⚠️ User creation returned {response.status_code}: {response.text}")
    except Exception as e:
        logging.error(f"💥 Failed to connect to registration: {str(e)}")

def get_access_token():
    try:
        response = requests.post(LOGIN_URL, json={"username": USERNAME, "password": PASSWORD})
        if response.status_code == 200:
            token = response.json().get("access_token")
            logging.info("✅ Successfully authenticated!")
            return token
        else:
            logging.error(f"❌ Authentication failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logging.error(f"💥 Failed to connect to login: {str(e)}")
        return None

def delete_all_dpps(token):
    """Deletes all existing DPPs to start fresh."""
    logging.info("🧹 Cleaning up old DPPs...")
    headers = {"Authorization": f"Bearer {token}"}

    try:
        # Search for all DPPs
        res = requests.post(SEARCH_URL, json={"search_mode": "simple", "keywords": " ", "limit": 100}, headers=headers)
        if res.status_code == 200:
            items = res.json().get("results", [])
            logging.info(f"Found {len(items)} existing DPPs to delete.")
            for item in items:
                del_res = requests.delete(f"{API_URL}{item['id']}", headers=headers)
                if del_res.status_code == 200:
                    print(f"   Deleted ID {item['id']}")
                else:
                    print(f"   Failed to delete ID {item['id']}")
        else:
            logging.warning("Could not fetch existing DPPs for cleanup.")
    except Exception as e:
        logging.error(f"Cleanup failed: {e}")

# --- NEW AAS-COMPLIANT DATASET (FULL LIST) ---
dpp_data = [
    # --- INDUSTRIAL (SIEMENS & ABB) ---
    {
        "title": "Siemens Simotics S-1FK7 Motor",
        "product_id": "SIE-MOT-1FK7-001",
        "manufacturer": "Siemens AG",
        "model_number": "1FK7063-2AF71-1RA0",
        "serial_number": "SN-98234122",
        "production_date": "2024-05-12",
        "submodels": [
            {
                "idShort": "TechnicalData",
                "semanticId": "https://admin-shell.io/ZVEI/TechnicalData/1/1",
                "submodelElements": {
                    "power_kw": 2.3, "torque_nm": 11, "speed_rpm": 3000, "efficiency_class": "IE4"
                }
            },
            {
                "idShort": "CarbonFootprint",
                "semanticId": "https://admin-shell.io/idta/CarbonFootprint/1/0",
                "submodelElements": {
                    "carbon_footprint_kg": 142.5, "calculation_method": "Cradle-to-Gate"
                }
            },
            {
                "idShort": "Circularity",
                "submodelElements": {
                    "material_copper_kg": 2.1, "repairability_index": 8.8
                }
            }
        ]
    },
    {
        "title": "Siemens Sinamics G120 Inverter",
        "product_id": "SIE-INV-G120-055",
        "manufacturer": "Siemens AG",
        "model_number": "6SL3210-1PE21-1AL0",
        "serial_number": "SN-77210983",
        "production_date": "2024-02-20",
        "submodels": [
            {
                "idShort": "ElectricalData",
                "submodelElements": {
                    "voltage": "400V", "current": "11A", "modular_design": True
                }
            },
            {
                "idShort": "Software",
                "submodelElements": {
                    "firmware_version": "v4.7"
                }
            },
            {
                "idShort": "CarbonFootprint",
                "submodelElements": {
                    "co2_footprint": "95kg"
                }
            }
        ]
    },
    {
        "title": "Siemens SIMATIC S7-1500 PLC",
        "product_id": "SIE-PLC-S7-1500",
        "manufacturer": "Siemens AG",
        "model_number": "6ES7511-1AK02-0AB0",
        "serial_number": "SN-88124411",
        "production_date": "2024-04-10",
        "submodels": [
            {
                "idShort": "TechnicalData",
                "submodelElements": {
                    "cpu_type": "CPU 1511-1 PN", "memory_mb": 150, "profinet_interface": True
                }
            },
            {
                "idShort": "PhysicalDimensions",
                "submodelElements": {
                    "display_size_inch": 3.45
                }
            },
            {
                "idShort": "EnergyEfficiency",
                "submodelElements": {
                    "energy_efficiency": "High"
                }
            }
        ]
    },
    {
        "title": "Siemens SIRIUS 3RW55 Soft Starter",
        "product_id": "SIE-SFT-3RW55",
        "manufacturer": "Siemens AG",
        "model_number": "3RW5513-1HA14",
        "serial_number": "SN-55112233",
        "production_date": "2024-03-05",
        "submodels": [
            {
                "idShort": "TechnicalData",
                "submodelElements": {
                    "power_kw": 5.5, "voltage_v": 480, "hybrid_switching": True
                }
            },
            {
                "idShort": "OperationalData",
                "submodelElements": {
                    "pump_cleaning_mode": True, "communication_module": "Profinet"
                }
            }
        ]
    },
    {
        "title": "Siemens SIMATIC ET 200SP",
        "product_id": "SIE-ET200SP-PN",
        "manufacturer": "Siemens AG",
        "model_number": "6ES7155-6AU01-0CN0",
        "serial_number": "SN-ET200-9988",
        "production_date": "2024-06-15",
        "submodels": [
            {
                "idShort": "EnvironmentalData",
                "submodelElements": {
                    "co2_footprint_kg": 8.5, "recyclability_rate": "92%"
                }
            },
            {
                "idShort": "TechnicalData",
                "submodelElements": {
                    "protection_class": "IP20", "bus_adapter": "BA 2xRJ45"
                }
            }
        ]
    },
    {
        "title": "Siemens SITOP PSU8600 Power Supply",
        "product_id": "SIE-PSU8600-40A",
        "manufacturer": "Siemens AG",
        "model_number": "6EP3437-8MB00-2CY0",
        "serial_number": "SN-PSU-776655",
        "production_date": "2024-05-20",
        "submodels": [
            {
                "idShort": "TechnicalData",
                "submodelElements": {
                    "efficiency_pct": 94, "profinet_support": True, "integrated_web_server": True
                }
            },
            {
                "idShort": "CarbonFootprint",
                "submodelElements": {
                    "co2_footprint_kg": 22.1
                }
            }
        ]
    },
    {
        "title": "ABB ACS880 Industrial Drive",
        "product_id": "ABB-DRV-880-012",
        "manufacturer": "ABB Group",
        "model_number": "ACS880-01-034A-3",
        "serial_number": "ABB-9912384",
        "production_date": "2023-11-15",
        "submodels": [
            {
                "idShort": "SafetyData",
                "submodelElements": {
                    "safety_level": "SIL3", "protection": "IP55"
                }
            },
            {
                "idShort": "Sustainability",
                "submodelElements": {
                    "energy_saving_mode": True, "recycled_plastic_pct": 15
                }
            }
        ]
    },
    # --- ELECTRONICS & BATTERIES (TESLA, SAMSUNG, APPLE) ---
    {
        "title": "Tesla Powerwall 2 Plus",
        "product_id": "TSL-PW2-2024",
        "manufacturer": "Tesla Inc.",
        "model_number": "PW2-13.5-G1",
        "serial_number": "BAT-7622910-B",
        "production_date": "2024-08-01",
        "submodels": [
            {
                "idShort": "BatteryPassport",
                "semanticId": "https://gba.org/battery-passport/1/0",
                "submodelElements": {
                    "capacity_kwh": 13.5, "chemistry": "NMC",
                    "cobalt_origin": "Congo", "lithium_origin": "Australia"
                }
            },
            {
                "idShort": "EndOfLife",
                "submodelElements": {
                    "instructions": "Return to Tesla Service Center"
                }
            }
        ]
    },
    {
        "title": "Samsung SDI Battery Cell 21700",
        "product_id": "SAM-CEL-21700-48G",
        "manufacturer": "Samsung SDI",
        "model_number": "INR21700-48G",
        "serial_number": "SAM-BATCH-44",
        "production_date": "2024-01-10",
        "submodels": [
            {
                "idShort": "TechnicalData",
                "submodelElements": {
                    "voltage_nominal": 3.6, "capacity_mah": 4800, "cycle_life": 1000
                }
            },
            {
                "idShort": "SafetyData",
                "submodelElements": {
                    "hazard_class": 9
                }
            }
        ]
    },
    {
        "title": "Apple iPad Pro M4",
        "product_id": "APL-IPD-M4-512",
        "manufacturer": "Apple Inc.",
        "model_number": "A2902",
        "serial_number": "APL-S9923KML",
        "production_date": "2024-06-01",
        "submodels": [
            {
                "idShort": "Circularity",
                "submodelElements": {
                    "rare_earth_recycled": 100, "aluminum_recycled": 100, "repairability_rating": "4/10"
                }
            },
            {
                "idShort": "BatteryHealth",
                "submodelElements": {
                    "battery_health_score": 100
                }
            }
        ]
    },
    # --- TEXTILES (PATAGONIA, LEVI'S) ---
    {
        "title": "Patagonia Nano Puff Jacket",
        "product_id": "PAT-NPF-BLU-M",
        "manufacturer": "Patagonia",
        "model_number": "84212",
        "serial_number": "PAT-2024-991",
        "production_date": "2024-03-15",
        "submodels": [
            {
                "idShort": "TextileComposition",
                "submodelElements": {
                    "material": "100% Recycled Polyester", "pfc_free": True
                }
            },
            {
                "idShort": "Sustainability",
                "submodelElements": {
                    "fair_trade_certified": True, "water_consumption_liters": 12.5
                }
            }
        ]
    },
    {
        "title": "Levi's 501 Original Jeans",
        "product_id": "LEV-501-DNM-32",
        "manufacturer": "Levi Strauss & Co.",
        "model_number": "00501-0101",
        "serial_number": "LEV-002133",
        "production_date": "2023-12-20",
        "submodels": [
            {
                "idShort": "MaterialData",
                "submodelElements": {
                    "organic_cotton_pct": 98, "microplastic_shedding": "Low"
                }
            },
            {
                "idShort": "Sustainability",
                "submodelElements": {
                    "water_less_technology": True, "traceability_score": "A"
                }
            }
        ]
    }
]

def seed_database():
    # Step 1: Create User
    create_user()
    
    # Step 2: Login
    token = get_access_token()
    if not token:
        logging.error("❌ Aborting seeding due to authentication failure.")
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Step 3: Delete Old Data (DISABLED FOR SAFETY)
    # delete_all_dpps(token)

    logging.info(f"🚀 Starting seeding of {len(dpp_data)} items...")
    for item in dpp_data:
        try:
            response = requests.post(API_URL, json=item, headers=headers)
            if response.status_code in [200, 201]:
                logging.info(f"✅ Success: {item['title']}")
            elif response.status_code == 400 and "already exists" in response.text:
                 logging.info(f"⏭️ Skipping {item['title']} (Backend reported duplicate)")
            else:
                logging.error(f"❌ Error {response.status_code} for {item['title']}: {response.text}")
        except Exception as e:
            logging.error(f"💥 Failed to connect: {str(e)}")

if __name__ == "__main__":
    seed_database()
