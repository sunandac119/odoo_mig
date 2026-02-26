# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import Controller, request
import serial
import time
import re
import binascii
import struct
import requests
import logging
_logger = logging.getLogger("Saturns===>")
# FieldsCOdeas: Hexs_Codeas
PURCHASE_RESPONSE_CODE_MAP = {'00': '3030', '01': '3031', '02': '3032', '65': '3635', '64': '3634', '29': '3239',
                              '30': '3330', 'D4': '4434', 'D5': '4435', '31': '3331', '32': '3332', '33': '3333',
                              '16': '3136', 'D1': '4431', 'D0': '4430', '50': '3530', '06': '3036', 'E0': '4530',
                              'E1': '4531', 'E2': '4532', 'E3': '4533', 'E4': '4534', 'E5': '4535', 'E6': '4536',
                              '03': '3033', '04': '3034', '38': '3338', 'D2': '4432', '17': '3137', '18': '3138',
                              '99': '3939', 'N1': '4e31', 'N2': '4e32', 'N3': '4e33'}

SATURN1000_TRANSACTION_CODE = {
    'purchase': 20
}


class Saturn1000PosPaymentsTerminals(http.Controller):

    @http.route('/pos/payment/saturn1000/payment_request_send', type='json', auth='user', csrf=False)
    def saturn1000_pos_payment_terminals_request_send(self, **kw):
        saturn1000_pm = request.env['pos.payment.method'].sudo().search([('use_payment_terminal', '=', 'saturn_1000')],limit=1)
        if saturn1000_pm:
            baudrate = saturn1000_pm.baudrate
            port = saturn1000_pm.saturn1000_serial_port
            timeout = 1
            try:

                amount = kw.get('amount')
                transaction_code = SATURN1000_TRANSACTION_CODE['purchase']
                transaction_id = kw.get('transactionId') or "00020230620090912971"
                transaction_id = re.sub(r'\D', '', transaction_id)
                transaction_id = transaction_id.rjust(20, '0')[:20]
                merchant_index = kw.get('merchantIndex') or "00"
                config_id = kw.get('configId')
                local_machines_tunneling_url = request.env['pos.config'].browse(config_id).local_pc_tunneling_url
                _logger.info("Serail ports is openeds................")
                hex_command = self.generatings_hex_command(amount, transaction_code, transaction_id, merchant_index)
                _logger.info(f"hex commnadeas ===> {hex_command}")
                _logger.info("Sending Updated Purchase Command...")
                payload = {
                    'hex_command': hex_command,
                }
                response = requests.post(f'{local_machines_tunneling_url}/send_command', json=payload)
                # # response = self.send_hex_command(port, baudrate, hex_command)
                if response.status_code !=200:
                    return {
                        'error':  response.text,
                    }
                # response = response.json()
                # if response.get('response') =="06":
                #     return {
                #         'error': response
                #     }
                _logger.info(f"Responseas commings froms pos termianls machineas==>{response.text}")
                response = response.json()
                if not response.get('response'):
                    return {
                        'error': response
                    }
                response = response.get('response').get('raw')
                # response= {}
                res = response.replace(" ", "")
                res_list = res.split("1C")
                res_list_length = len(res_list)
                line_first = res_list[0]
                res_dict={}
                for line in res_list[1:res_list_length - 2]:
                    line_length = len(line)
                    field_code_hex = line[:4]
                    field_char_ascii = bytes.fromhex(field_code_hex).decode("ascii")
                    field_value_hex = line[8:]  # 2 ==> foreas ans "1C"
                    field_value_ascii = bytes.fromhex(field_value_hex).decode("ascii")
                    print(f"{field_char_ascii}   ===>{field_value_ascii}" + "\n")

                    if field_char_ascii == "02" and field_value_ascii.replace(' ','') in ["TRANSACTIONNOTSUCCESS","USERABORT"]:
                        return {
                            'error': "TRANSACTION NOT SUCCESS"
                        }

                    if field_char_ascii == "66":
                        res_dict.update({
                            'transaction_id':field_value_ascii
                        })
                    elif field_char_ascii == "01":
                        res_dict.update({
                            'approval_code': field_value_ascii
                        })
                    elif field_char_ascii == "65":
                        res_dict.update({
                            'payment_terminal_inv_no': field_value_ascii
                        })
                    elif field_char_ascii == "64":
                        res_dict.update({
                            'trace_no': field_value_ascii
                        })
                    elif field_char_ascii == "16":
                        res_dict.update({
                            'payments_terminal_id': field_value_ascii
                        })
                    elif field_char_ascii == "06":
                        res_dict.update({
                            'retrival_ref_no': field_value_ascii
                        })

                last_line = res_list[res_list_length - 1]
                return {
                    'success': "ok",'data':res_dict
                }

            except Exception as e:
                return {
                    'error': e,
                }

        else:
            return {
                'error': "Saturn 1000 Payments Methods was not setups!!!!!!",
            }

    def calculate_lrc(self, message):
        byte_data = bytes.fromhex(message)
        lrc = 0x00
        for byte in byte_data:
            lrc ^= byte
        return lrc

    def generatings_hex_command(self, amount, transaction_code, transaction_id, merchant_index):
        # Start of Text (STX)
        start_of_text = "02"

        # Message Length (as specified in your example)
        message_length = b'\x00\x92'  # Length in hexadecimal (0x0092)

        # Transport Header
        transport_header_type = "60".encode('ascii').hex()  # Assuming '60' for Application Message
        transport_destination = "0000".encode('ascii').hex()  # Example: Destination ID
        transport_source = "0000".encode('ascii').hex()  # Example: Source ID
        transport_header = transport_header_type + transport_destination + transport_source

        # Presentation Header
        format_version = "1".encode('ascii').hex()  # Version 1
        request_response_indicator = "0".encode('ascii').hex()  # Request
        transaction_code_hex = str(transaction_code).encode(
            'ascii').hex()  # Convert transaction code to a single byte in hex
        response_code = "00".encode('ascii').hex()  # Response code (00 for requests)
        more_to_follow = "0".encode('ascii').hex()  # No more data to follow
        end_of_presentation_header = "1C"
        # End of presentation header marker
        presentation_header = (format_version + request_response_indicator +
                               transaction_code_hex + response_code +
                               more_to_follow + end_of_presentation_header)

        # Field 00: Placeholder (20 zeros, represented as 32 bytes in hex) Pay Account ID
        field_00_code = "00".encode('ascii').hex()
        field_00_data = "00000000000000000000".encode('ascii').hex()  # ASCII for "00000000000000000000"
        field_00 = field_00_code + "0020" + field_00_data + "1C"  # Field 00 combined with its length and data

        # Field 66: Transaction ID (provided as input, 32 bytes in hex)
        field_66_code = "66".encode('ascii').hex()
        # transaction_id_hex = ''.join([f'\\x{hex(ord(char))[2:].zfill(2)}' for char in transaction_id]) # Convert transaction ID to hex
        transaction_id_hex = transaction_id.encode('ascii').hex()
        field_66 = field_66_code + "0020" + transaction_id_hex + "1C"  # Field 66 combined with its length and data

        # Field 40: Amount (convert integer amount to 12-digit string, then to hex)
        field_40_code = "40".encode('ascii').hex()

        int_amount = int(amount)
        decimal_amount = int(round((amount - int_amount)*100,2))
        decimal_amount = f"{decimal_amount:002d}"
        amounts = int(str(int_amount)+decimal_amount)
        amount = f"{amounts:012d}"  # Format amount as a 12-digit string
        # packed = struct.pack('!f', amount)  # ! means network (= big-endian) byte order
        # hex_string = ''.join([f'\\x{byte:02x}' for byte in packed])
        amount_hex = amount.encode('ascii').hex()
        # amount_hex = binascii.hexlify(amount_in_cents.encode('ascii')).upper()  # Convert to hex

        field_40 = field_40_code + "0012" + amount_hex + "1C"  # Field 40 combined with its length and data


        # Field M1: Merchant Index (provided as input, 2 bytes in hex)
        field_m1_code = 'M1'.encode('ascii').hex()  # ASCII "M1" -> 4D31 in hex
        # if merchant_index == '99':
        #     field_m1_code = 'W1'.encode('ascii').hex()
        # merchant_index_hex = ''.join([f'\\x{hex(ord(char))[2:].zfill(2)}' for char in merchant_index])  # Convert Merchant Index to hex
        merchant_index_hex = merchant_index.encode('ascii').hex()
        field_m1 = field_m1_code + "0002" + merchant_index_hex + "1C"  # Field M1 combined with its length and data

        # Combine all Field Data
        combined_field_data = field_00 + field_66 + field_40 + field_m1

        # Combine all parts to form the full message
        message_data = transport_header + presentation_header + combined_field_data
        message_length = len(message_data) // 2
        full_message = start_of_text + "00" + str(message_length) + message_data

        # End of Text (ETX)
        end_of_text = "03"
        crc_msg = "00" + str(message_length) + message_data + end_of_text
        # Calculate LRC (Longitudinal Redundancy Check)
        # message = full_message[1:] + end_of_text
        lrc = self.calculate_lrc(crc_msg)
        lrc = f"{lrc:02X}"
        # Final message with STX, ETX, and LRC
        hex_commands = full_message + end_of_text + lrc
        # hex_commands = binascii.hexlify(final_message).upper().decode('utf-8')
        return hex_commands

        # return True

    # def send_hex_command(port, baudrate, hex_command):
    #     try:
    #         with serial.Serial(port, baudrate, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
    #                            bytesize=serial.EIGHTBITS) as ser:
    #             # Convert hex string to bytes and send the data to the ECR
    #             ser.write(bytes.fromhex(hex_command))
    #             # Allow some time for the ECR to process and respond
    #             time.sleep(1)  # Adjust this delay as needed
    #
    #             # Read the response from the ECR
    #             response = ser.read(1024)  # Adjust the size as per expected response
    #             # Print the response
    #             return {
    #                 'success':response
    #             }
    #     except Exception as e:
    #         return {
    #             'error':e
    #         }