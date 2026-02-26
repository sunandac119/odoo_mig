from lxml import etree
from OpenSSL import crypto
from xml.dom.minidom import parseString
from io import BytesIO
import os
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes, serialization
# Constants
SOURCE_FILE_PATH = "/Users/onlymac/Downloads/lhdn_INV_2024_00172.xml"
CERT_FILE_PATH = "/Users/onlymac/workspace/odoo_v17/custom_addons/ap_addon_17/certificate.pem"
TARGET_FILE_PATH = "/Users/onlymac/Downloads/signed_invoice.xml"
KEYSTORE_PASS = "Al8#Q(Xs"
pk_final_path = "/Users/onlymac/workspace/odoo_v17/custom_addons/ap_addon_17/private_key.pem"

def main():
    # Load the XML document
    tree = etree.parse(SOURCE_FILE_PATH)
    root = tree.getroot()

    # Load the certificate and private key from PKCS12 keystore
    with open(CERT_FILE_PATH, 'rb') as f:
        cert = x509.load_pem_x509_certificate(f.read(), backend=default_backend())
        # p12 = crypto.load_pkcs12(f.read(), KEYSTORE_PASS.encode())
        # cert = p12.get_certificate()
        # private_key = p12.get_privatekey()

    # Create DSSDocument from XML
    to_sign_document = BytesIO(etree.tostring(root))

    # Create the certificate token
    signing_certificate = crypto.X509.from_cryptography(cert)

    # Initialize signature parameters
    signed_info_canonicalization_method = "http://www.w3.org/2006/12/xml-c14n11"
    signature_packaging = "enveloped"
    signature_level = "XAdES_BASELINE_B"
    signing_certificate_digest_method = "sha256"
    signed_properties_canonicalization_method = "http://www.w3.org/2006/12/xml-c14n11"

    # Prepare transformations
    transforms = [
        "not(//ancestor-or-self::ext:UBLExtensions)",
        "not(//ancestor-or-self::cac:Signature)",
        "http://www.w3.org/2006/12/xml-c14n11"
    ]

    # Load the private key from a file (PEM format)
    with open(pk_final_path, 'rb') as key_file:
        private_key = load_pem_private_key(key_file.read(), password="yash".encode(), backend=default_backend())

    # Sign the document
    signed_data = private_key.sign(
            to_sign_document.getvalue(),
            padding.PKCS1v15(),
            hashes.SHA256()
        )

    # Parse the signed document
    signed_xml_document = etree.fromstring(signed_data)

    # Insert the signature into the correct place in the XML
    invoice_element = signed_xml_document.find(".//{urn:oasis:names:specification:ubl:schema:xsd:Invoice-2}Invoice")
    ubl_extensions_element = etree.Element(
        "{urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2}ext:UBLExtensions")

    ubl_extension_element = etree.Element(
        "{urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2}ext:UBLExtension")
    extension_uri_element = etree.Element(
        "{urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2}ext:ExtensionURI")
    extension_uri_element.text = "urn:oasis:names:specification:ubl:dsig:enveloped:xades"
    extension_content_element = etree.Element(
        "{urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2}ext:ExtensionContent")

    ubl_document_signatures_element = signed_xml_document.find(".//{http://www.w3.org/2000/09/xmldsig#}Signature")

    sig_element = etree.Element(
        "{urn:oasis:names:specification:ubl:schema:xsd:CommonSignatureComponents-2}sig:UBLDocumentSignatures", nsmap={
            'sig': 'urn:oasis:names:specification:ubl:schema:xsd:CommonSignatureComponents-2',
            'sac': 'urn:oasis:names:specification:ubl:schema:xsd:SignatureAggregateComponents-2',
            'sbc': 'urn:oasis:names:specification:ubl:schema:xsd:SignatureBasicComponents-2'
        })

    sac_signature_information_element = etree.Element(
        "{urn:oasis:names:specification:ubl:schema:xsd:SignatureAggregateComponents-2}sac:SignatureInformation")
    cbc_id_element = etree.Element("{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}cbc:ID")
    cbc_id_element.text = "urn:oasis:names:specification:ubl:signature:1"
    sbc_referenced_signature_id_element = etree.Element(
        "{urn:oasis:names:specification:ubl:schema:xsd:SignatureBasicComponents-2}sbc:ReferencedSignatureID")
    sbc_referenced_signature_id_element.text = "urn:oasis:names:specification:ubl:signature:Invoice"

    sac_signature_information_element.append(cbc_id_element)
    sac_signature_information_element.append(sbc_referenced_signature_id_element)
    sac_signature_information_element.append(ubl_document_signatures_element)

    sig_element.append(sac_signature_information_element)
    extension_content_element.append(sig_element)
    ubl_extension_element.append(extension_uri_element)
    ubl_extension_element.append(extension_content_element)
    ubl_extensions_element.append(ubl_extension_element)

    invoice_element.insert(0, ubl_extensions_element)

    # Save the signed and modified document
    with open(TARGET_FILE_PATH, 'wb') as f:
        f.write(etree.tostring(signed_xml_document))

    print("Invoice signed successfully!")


if __name__ == "__main__":
    main()





from locust import task, between
from OdooLocust.OdooLocustUser import OdooLocustUser
class Seller(OdooLocustUser):
    wait_time = between(0.1, 10)
    host = '127.0.0.1'
    database = "all_its_odoos_v17Ent_29_juneas_dbs_backusups"
    login = "admin"
    password = "admin"
    port = 8071
    protocol = "jsonrpc"

    @task(10)
    def read_partners(self):
        pos_config_model = self.client.get_model('pos.config')
        config_ids = pos_config_model.search([('id','=',7)])
        config_ids[0].open_ui()