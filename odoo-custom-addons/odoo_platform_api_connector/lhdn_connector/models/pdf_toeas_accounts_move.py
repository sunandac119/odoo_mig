# from invoice2data import extract_data
# # from camelot.io import read_pdf
# # result = extract_data('/Users/onlymac/Downloads/teo.pdf')
#
# import fitz  # PyMuPDF
# import json
# from PIL import Image
# import io
# import base64
#
#
#
# # Function to convert images to base64
# def image_to_base64(image):
#     buffer = io.BytesIO()
#     image.save(buffer, format="JPEG")
#     return base64.b64encode(buffer.getvalue()).decode()
#
#
# # Function to extract text and images from PDF
# def extract_pdf_data(pdf_path):
#     data = {"text": [], "images": []}
#     document = fitz.open(pdf_path)
#
#     for page_number in range(len(document)):
#         page = document[page_number]
#
#         # Extract text
#         text = page.get_text()
#         data["text"].append({"page": page_number + 1, "content": text})
#
#         # Extract images
#         for image_index, img in enumerate(page.get_images(full=True)):
#             xref = img[0]
#             base_image = document.extract_image(xref)
#             image_bytes = base_image["image"]
#             image = Image.open(io.BytesIO(image_bytes))
#             data["images"].append({
#                 "page": page_number + 1,
#                 "image_index": image_index + 1,
#                 "base64": image_to_base64(image)
#             })
#
#     return data
#
#
# # Replace 'your_file.pdf' with the path to your PDF file
# pdf_path = '/Users/onlymac/Downloads/teo.pdf'
# extracted_data = extract_pdf_data(pdf_path)
#
# # Convert the extracted data to JSON format
# json_data = json.dumps(extracted_data, indent=4)
#
# # Save to a JSON file
# output_path = '/mnt/data/extracted_data.json'
# with open(output_path, 'w') as f:
#     f.write(json_data)
#
# print(f"Data extraction complete. Check '{output_path}'.")
#
# # import pdfplumber
# #
# # # Open the PDF file
# # with pdfplumber.open('/Users/onlymac/Downloads/teo.pdf') as pdf:
# #     # Iterate over each page
# #     for page in pdf.pages:
# #         # Extract tables from the page
# #         table = page.extract_table()
# #         if table:
# #             # Print each row of the table
# #             for row in table:
# #                 print(row)
