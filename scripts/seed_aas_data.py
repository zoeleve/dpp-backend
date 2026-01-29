import requests
import json
import os
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

# Configuration
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
LOGIN_URL = f"{BASE_URL}/auth/login"
REGISTER_URL = f"{BASE_URL}/users/"
API_URL = f"{BASE_URL}/dpp/json/"

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
        elif response.status_code == 400:
            logging.info("ℹ️ User likely already exists.")
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

def wipe_database(token):
    """Deletes ALL existing DPPs to ensure a clean slate."""
    logging.info("☢️  WIPING DATABASE: Deleting ALL existing DPPs...")
    headers = {"Authorization": f"Bearer {token}"}
    
    deleted_count = 0
    
    while True:
        try:
            # Search for everything. 
            # We use " " as keyword, and limit 100 (max allowed by schema)
            res = requests.post(f"{BASE_URL}/dpp/json/search", json={
                "search_mode": "simple",
                "keywords": " ", 
                "limit": 100
            }, headers=headers)
            
            if res.status_code == 200:
                items = res.json().get("results", [])
                if not items:
                    break # No more items

                for item in items:
                    dpp_id = item.get("id")
                    del_res = requests.delete(f"{API_URL}{dpp_id}", headers=headers)
                    if del_res.status_code == 200:
                        deleted_count += 1
                        print(f"   - Deleted ID {dpp_id} (Total: {deleted_count})", end="\r")
                    else:
                        logging.warning(f"   - Failed to delete ID {dpp_id}: {del_res.status_code}")
                
                # If we got fewer than limit, we are done
                if len(items) < 100:
                    break
            else:
                logging.warning(f"⚠️ Could not fetch items to delete: {res.status_code} - {res.text}")
                break
                
        except Exception as e:
            logging.error(f"💥 Failed to wipe database: {str(e)}")
            break
            
    print("") # Newline
    if deleted_count > 0:
        logging.info(f"✅ Database wiped. Deleted {deleted_count} records.")
    else:
        logging.info("✅ Database was already empty.")


# --- RICH AAS DATASET ---
aas_data = [
    # 1. Industrial Motor (Siemens Style)
    {
        "title": "High-Efficiency Servo Motor 1FK7",
        "product_id": "did:siemens:motor:1FK7063-2AF71",
        "manufacturer": "Siemens AG",
        "model_number": "1FK7063-2AF71-1RA0",
        "serial_number": "SN-2024-MOT-998811",
        "production_date": "2024-05-15",
        "submodels": [
            {
                "idShort": "TechnicalData",
                "semanticId": "https://admin-shell.io/ZVEI/TechnicalData/1/1",
                "submodelElements": {
                    "RatedPower": "2.3 kW",
                    "RatedTorque": "11 Nm",
                    "MaxSpeed": "6000 rpm",
                    "Voltage": "400 V",
                    "EfficiencyClass": "IE4 (Super Premium Efficiency)",
                    "CoolingType": "Natural Convection",
                    "ProtectionClass": "IP65"
                }
            },
            {
                "idShort": "CarbonFootprint",
                "semanticId": "https://admin-shell.io/idta/CarbonFootprint/1/0",
                "submodelElements": {
                    "CO2_Total": "142.5 kgCO2e",
                    "ProductStage_A1_A3": "120.1 kgCO2e",
                    "Distribution_A4": "5.2 kgCO2e",
                    "UseStage_B6": "Based on EU Mix",
                    "CalculationStandard": "ISO 14067:2018",
                    "VerificationStatus": "Third-Party Verified"
                }
            },
            {
                "idShort": "DigitalNameplate",
                "semanticId": "https://admin-shell.io/zvei/nameplate/1/0/Nameplate",
                "submodelElements": {
                    "ManufacturerName": "Siemens AG",
                    "ManufacturerAddress": "Werner-von-Siemens-Straße 1, Munich, Germany",
                    "YearOfConstruction": "2024",
                    "CE_Marking": True,
                    "UL_Certification": "E123456"
                }
            }
        ]
    },

    # 2. EV Battery (Tesla/GBA Style)
    {
        "title": "EV Battery Module 75kWh",
        "product_id": "did:gba:battery:75kwh-nmc-2024",
        "manufacturer": "Gigafactory Berlin",
        "model_number": "BAT-MOD-75-NMC",
        "serial_number": "GFB-24-99123-X",
        "production_date": "2024-06-01",
        "submodels": [
            {
                "idShort": "BatteryPassport",
                "semanticId": "https://gba.org/battery-passport/1/0",
                "submodelElements": {
                    "BatteryCategory": "LMT (Light Means of Transport)",
                    "Chemistry": "NMC (Nickel Manganese Cobalt)",
                    "RatedCapacity": "75 kWh",
                    "Weight": "480 kg",
                    "ExpectedCycleLife": "2000 cycles @ 80% DoD",
                    "StateOfHealth": "100%"
                }
            },
            {
                "idShort": "MaterialComposition",
                "submodelElements": {
                    "Cobalt": "12 kg (Origin: DRC, Certified Conflict-Free)",
                    "Lithium": "8 kg (Origin: Australia)",
                    "Nickel": "45 kg",
                    "RecycledContent_Cobalt": "15%",
                    "RecycledContent_Lithium": "5%"
                }
            },
            {
                "idShort": "CarbonFootprint",
                "submodelElements": {
                    "CO2_Total": "4500 kgCO2e",
                    "CarbonIntensity": "60 kgCO2e/kWh",
                    "EnergySource_Manufacturing": "100% Renewable (Wind/Solar)"
                }
            }
        ]
    },

    # 3. Smart Phone (Fairphone/Apple Style)
    {
        "title": "EcoSmart Phone Pro 5",
        "product_id": "did:tech:phone:pro5-128gb",
        "manufacturer": "EcoTech Devices",
        "model_number": "ET-PRO5-128",
        "serial_number": "ET-9921-XM",
        "production_date": "2024-03-10",
        "submodels": [
            {
                "idShort": "Repairability",
                "semanticId": "https://ec.europa.eu/repair-score",
                "submodelElements": {
                    "RepairScore": "9.2/10",
                    "SparePartsAvailability": "7 Years",
                    "DisassemblySteps_Battery": "3 Steps (No Glue)",
                    "DisassemblySteps_Screen": "5 Steps"
                }
            },
            {
                "idShort": "TechnicalData",
                "submodelElements": {
                    "Processor": "Snapdragon 8 Gen 2",
                    "RAM": "8 GB",
                    "Storage": "128 GB",
                    "Screen": "6.1 inch OLED",
                    "Battery": "4000 mAh (Replaceable)"
                }
            },
            {
                "idShort": "SupplyChain",
                "submodelElements": {
                    "Gold_Origin": "Fairtrade Certified",
                    "Tungsten_Origin": "Conflict-Free Smelter Program",
                    "AssemblyLocation": "Vietnam (SA8000 Certified Factory)"
                }
            }
        ]
    },

    # 4. Sustainable Textile (Patagonia Style)
    {
        "title": "Recycled Ocean Plastic Jacket",
        "product_id": "did:textile:jacket:ocean-blue-l",
        "manufacturer": "GreenWear Apparel",
        "model_number": "GW-JKT-2024-BLU",
        "serial_number": "GW-8821-L",
        "production_date": "2024-01-20",
        "submodels": [
            {
                "idShort": "MaterialComposition",
                "semanticId": "https://textile-exchange.org/standards/",
                "submodelElements": {
                    "MainFabric": "100% Recycled Polyester (rPET) from Ocean Plastic",
                    "Lining": "100% Organic Cotton",
                    "Zipper": "YKK Natulon (Recycled Tape)",
                    "Chemicals": "PFC-Free DWR Coating"
                }
            },
            {
                "idShort": "Circularity",
                "submodelElements": {
                    "Recyclability": "100% (Mono-material design)",
                    "TakeBackProgram": "Available via QR Code scan",
                    "WashingInstructions": "Wash cold (30°C), Line dry to reduce microfibers"
                }
            },
            {
                "idShort": "SocialImpact",
                "submodelElements": {
                    "FactoryCertification": "Fair Trade USA",
                    "LivingWageGap": "0% (Living Wage Paid)"
                }
            }
        ]
    },

    # 5. Industrial Pump (Grundfos Style)
    {
        "title": "Smart Digital Dosing Pump",
        "product_id": "did:pump:smart-dose-ddc",
        "manufacturer": "FlowMaster Systems",
        "model_number": "DDC-6-10",
        "serial_number": "FM-PUMP-7721",
        "production_date": "2024-04-05",
        "submodels": [
            {
                "idShort": "OperationalData",
                "submodelElements": {
                    "MaxFlow": "6 l/h",
                    "MaxPressure": "10 bar",
                    "TurndownRatio": "1:1000",
                    "Connectivity": "Modbus TCP, Profinet, Bluetooth"
                }
            },
            {
                "idShort": "Maintenance",
                "submodelElements": {
                    "NextServiceDue": "2025-04-05",
                    "DiaphragmLife": "20,000 hours",
                    "PredictiveMaintenance": "Enabled (Vibration Analysis)"
                }
            },
            {
                "idShort": "Documentation",
                "submodelElements": {
                    "Manual_URL": "https://flowmaster.com/docs/ddc-6-10.pdf",
                    "3D_CAD_Model": "https://flowmaster.com/cad/ddc-6-10.step",
                    "WiringDiagram": "https://flowmaster.com/wiring/ddc-series.pdf"
                }
            }
        ]
    }
]

def seed_database():
    create_user()
    token = get_access_token()
    if not token:
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # 1. Wipe everything first
    wipe_database(token)

    # 2. Seed new data
    logging.info(f"🚀 Seeding {len(aas_data)} AAS-compliant DPPs...")
    for item in aas_data:
        try:
            response = requests.post(API_URL, json=item, headers=headers)
            if response.status_code in [200, 201]:
                logging.info(f"✅ Created: {item['title']}")
                
                # 3. Publish it
                dpp_id = response.json()['id']
                requests.put(f"{API_URL}{dpp_id}/publish", headers=headers)
                
                time.sleep(0.5)
            else:
                logging.error(f"❌ Error {response.status_code}: {response.text}")
        except Exception as e:
            logging.error(f"💥 Failed: {str(e)}")

if __name__ == "__main__":
    seed_database()
