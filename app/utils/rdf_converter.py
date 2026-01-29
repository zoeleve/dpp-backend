from rdflib import Graph, Literal, RDF, URIRef, Namespace
from rdflib.namespace import XSD, DCTERMS, FOAF
from app.models.dpp import DPP
from app.configs.config import settings

# Define Namespaces
# Use a stable URI for the data, independent of the infrastructure hostname
RDF_BASE_URI = "http://dpp-platform.org"
DPP_NS = Namespace(f"{RDF_BASE_URI}/dpp/")
AAS = Namespace("https://admin-shell.io/aas/3/0/")
SCHEMA = Namespace("http://schema.org/")

def convert_dpp_to_rdf(dpp: DPP) -> str:
    """
    Converts a DPP SQLAlchemy model instance into an RDF Turtle string.
    """
    try:
        g = Graph()
        g.bind("dpp", DPP_NS)
        g.bind("aas", AAS)
        g.bind("dcterms", DCTERMS)
        g.bind("schema", SCHEMA)

        # Define the Subject URI
        dpp_uri = DPP_NS[str(dpp.dpp_uuid)]

        # Add Basic Triples
        g.add((dpp_uri, RDF.type, AAS.AssetAdministrationShell))
        g.add((dpp_uri, DCTERMS.title, Literal(dpp.title, datatype=XSD.string)))
        g.add((dpp_uri, DCTERMS.identifier, Literal(dpp.dpp_uuid, datatype=XSD.string)))
        
        if dpp.created_at:
            g.add((dpp_uri, DCTERMS.created, Literal(dpp.created_at, datatype=XSD.dateTime)))
        
        if dpp.is_published:
            g.add((dpp_uri, SCHEMA.creativeWorkStatus, Literal("Published")))
        else:
            g.add((dpp_uri, SCHEMA.creativeWorkStatus, Literal("Draft")))

        # Extract Data from JSONB
        data = dpp.dpp_data
        
        if data and isinstance(data, dict):
            # Manufacturer
            if "manufacturer" in data and data["manufacturer"]:
                g.add((dpp_uri, SCHEMA.manufacturer, Literal(data["manufacturer"])))
            
            # Model Number
            if "model_number" in data and data["model_number"]:
                g.add((dpp_uri, SCHEMA.model, Literal(data["model_number"])))

            # Handle Submodels (AAS Structure)
            if "submodels" in data and isinstance(data["submodels"], list):
                for sm in data["submodels"]:
                    if not isinstance(sm, dict):
                        continue

                    # Create a URI for the Submodel
                    sm_id = sm.get("idShort", "UnknownSubmodel").replace(" ", "_")
                    sm_uri = DPP_NS[f"{dpp.dpp_uuid}/{sm_id}"]
                    
                    # Link DPP to Submodel
                    g.add((dpp_uri, AAS.submodel, sm_uri))
                    g.add((sm_uri, RDF.type, AAS.Submodel))
                    g.add((sm_uri, DCTERMS.title, Literal(sm.get("idShort", "Unknown"))))
                    
                    if "semanticId" in sm and sm["semanticId"]:
                        g.add((sm_uri, AAS.semanticId, URIRef(sm["semanticId"])))

                    # Add Submodel Elements
                    elements = sm.get("submodelElements", {})
                    if elements and isinstance(elements, dict):
                        for key, value in elements.items():
                            # Simple key-value mapping for elements
                            g.add((sm_uri, AAS.submodelElement, Literal(f"{key}: {value}")))

        # Return as Turtle format string
        return g.serialize(format="turtle")
        
    except Exception as e:
        print(f"Error converting DPP {dpp.dpp_uuid}: {e}")
        raise e
