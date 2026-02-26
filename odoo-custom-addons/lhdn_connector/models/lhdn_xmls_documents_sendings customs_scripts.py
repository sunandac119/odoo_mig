from lxml import etree
import os
import base64
import hashlib
import requests
import json
import time
# def generate_document_hash(self, xml_content_base64_string):
#     # Hash the XML content using SHA-256
#     sha256_hash = hashlib.sha256(xml_content_base64_string).hexdigest()
#     return sha256_hash
def clean_up_node(node):
    # Example cleanup: Remove empty elements and strip text
    for elem in node.xpath(".//*"):
        if elem.text:
            elem.text = elem.text.strip()
        if elem.tail:
            elem.tail = elem.tail.strip()
        if not elem.text and len(elem) == 0:
            elem.getparent().remove(elem)

    return node

lhdn_api_client_id = "cecc0460-26ef-4c36-8153-6487ca48f2b1"
lhdn_api_client_password = "9e0de30a-d9a9-4b90-8734-52803511e354"
lhdn_base_url = "https://preprod-api.myinvois.hasil.gov.my"

headers = {
    'Content-Type': 'application/x-www-form-urlencoded'
}
payload = {'client_id': lhdn_api_client_id,
           'client_secret': lhdn_api_client_password,
           'grant_type': 'client_credentials',
           'scope': 'InvoicingAPI'
           }
res = requests.post(lhdn_base_url + '/connect/token', data=payload,
                    headers=headers)
res = res.json()
if res.get('access_token'):
    access_token = res.get('access_token')

    # Define the path to the XML file in the Downloads folder
    xml_file_path = os.path.expanduser('/Users/onlymac/Downloads/lhdn_INV_2024_00181_signed.xml')

    # Load the XML file
    tree = etree.parse(xml_file_path)

    # Get the root element
    root = tree.getroot()

    # # Convert the XML to a string
    # xml_content = etree.tostring(root, pretty_print=True).decode()

    xml_content = etree.tostring(root, xml_declaration=True, encoding='UTF-8')

    xml_content_base64_string = base64.b64encode(xml_content)

    documents_list = []

    documents_sha256_hash = hashlib.sha256(xml_content).hexdigest()

    documents_list.append({"format": "XML", "documentHash": documents_sha256_hash, "codeNumber": "INV/2024/00177",
                           "document": xml_content_base64_string.decode("utf-8")})

    submit_headers = headers = {'Content-Type': 'application/json',
                                'Authorization': f'Bearer {access_token}'}

    # This is only for the single documents submission
    submit_payload = {"documents": documents_list}

    submit_payload = json.dumps(submit_payload)

    result = requests.post(lhdn_base_url + '/api/v1.0/documentsubmissions', data=submit_payload, headers=submit_headers)

    result = result.json()
    if result.get('acceptedDocuments'):
        uuid = result.get('acceptedDocuments')[0].get('uuid')
        print(f"Documents submittedd successfullys UUID ==> {uuid}")
        time.sleep(20)
        get_documents_info = requests.get(
            lhdn_base_url + f'/api/v1.0/documents/{uuid}/details',
            headers={'Authorization': f'Bearer {access_token}'}, data={})
        submitted_documents_info = get_documents_info.json()
        print(json.dumps(submitted_documents_info,indent=4))
    else:
        print(f"Errors ==> {json.dumps(result,indent=4)}")

else:
    print("LHDN Access Tokens was not generatedds")

    'Invoice.UBLExtensions.UBLExtensions.ExtensionContent.UBLDocumentSignatures.SignatureInformation.Signature.SignedInfo.Reference@Type="http://uri.etsi.org/01903/v1.3.2#SignedProperties".DigestValue'