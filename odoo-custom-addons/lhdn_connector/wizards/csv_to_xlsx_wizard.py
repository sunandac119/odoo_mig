import base64
import csv
import tempfile
import xlsxwriter
from odoo import models, fields, api
from odoo.exceptions import UserError


class CSVtoXLSXWizard(models.TransientModel):
    _name = 'csv.to.xlsx.wizard'
    _description = 'Wizard to Upload CSV and Generate XLSX'

    csv_file = fields.Binary(string="CSV File", required=True)
    csv_filename = fields.Char(string="CSV File Name")
    processed_file = fields.Binary(string="Generated XLSX File", readonly=True)
    processed_filename = fields.Char(string="Generated XLSX Filename", readonly=True)

    def process_csv(self):
        """
        Process the uploaded CSV file, apply custom logic, and generate an XLSX file.
        """
        if not self.csv_file:
            raise UserError("Please upload a CSV file.")

        # Decode the uploaded file from base64 to a readable CSV
        csv_data = base64.b64decode(self.csv_file)
        csv_tempfile = tempfile.NamedTemporaryFile(delete=False, suffix='.csv')
        csv_tempfile.write(csv_data)
        csv_tempfile.close()

        # Open the CSV file and apply your custom logic
        # rows = []
        missings_documents = []
        validated_invoice = []
        invalid_invoice = []
        rejected_invoice = []
        cancelled_invoice = []


        einv_submission_vs_irbm_validations = []
        einv_submission_vs_irbm_validations_meta_data = {'total':0,'accepted':0,'rejected':0}
        rejected_e_inv_by_lhdn = []
        rejected_e_inv_by_lhdn_meta_data = {'total':0,'corrected':0,'accepted':0}
        cancelled_e_invoice_by_bank_islam = []
        cancelled_e_invocie_by_bank_islam_meta_data = {'total':0}

        with open(csv_tempfile.name, mode='r') as file:
            csv_reader = csv.reader(file)
            header = next(csv_reader)  # Assuming the first row is the header
            for row in csv_reader:
                # Append each row to the `rows` list for further processing
                # rows.append(row)
                csv_inv_number = row[3]
                inv_record = self.env['account.move'].search([('portal_ai_inv_number', '=', csv_inv_number)], limit=1)
                if inv_record:
                    if inv_record.lhdn_invoice_status == "validated":
                        validated_invoice.append(csv_inv_number)
                    elif inv_record.lhdn_invoice_status in ["error", "submitted"]:
                        invalid_invoice.append({csv_inv_number: inv_record.lhdn_documents_error})
                    elif inv_record.lhdn_invoice_status == "rejected":
                        rejected_invoice.append(csv_inv_number)
                    elif inv_record.lhdn_invoice_status == "cancelled":
                        cancelled_invoice.append(csv_inv_number)

                    einv_submission_vs_irbm_validations.append({
                        'inv_number':csv_inv_number,
                        'submission_date':inv_record.invoice_date,
                        'amount':inv_record.amount_total_signed,
                        'validation_status':inv_record.lhdn_invoice_status,
                        'remark':inv_record.lhdn_documents_error if inv_record.lhdn_documents_error else "No Issueas"
                    })
                    einv_submission_vs_irbm_validations_meta_data.update({
                        'total':einv_submission_vs_irbm_validations_meta_data.get('total')+1,
                        'accepted': einv_submission_vs_irbm_validations_meta_data.get('accepted')+1 if inv_record.lhdn_invoice_status == "validated" else einv_submission_vs_irbm_validations_meta_data.get('accepted'),
                        'rejected':einv_submission_vs_irbm_validations_meta_data.get('rejected')+1 if inv_record.lhdn_invoice_status == "error" else einv_submission_vs_irbm_validations_meta_data.get('rejected'),
                    })

                    if inv_record.lhdn_invoice_status == "error":
                        rejected_e_inv_by_lhdn.append({
                            'inv_number':csv_inv_number,
                            'rejected_reason':inv_record.lhdn_documents_error,
                            'resolution_steps':"Corrected Errors",
                            're_submission_date':inv_record.invoice_date,
                            'status':inv_record.lhdn_invoice_status
                        })
                        rejected_e_inv_by_lhdn_meta_data.update({
                            'total':rejected_e_inv_by_lhdn_meta_data.get('total')+1
                        })
                    if inv_record.lhdn_invoice_status == "cancelled":
                        cancelled_e_invoice_by_bank_islam.append({
                            'inv_number':csv_inv_number,
                            'cancellation_date':inv_record.invoice_date,
                            'reason':inv_record.lhdn_document_cancellation_reason,
                            'gl_update':"GL Update",
                            'lhdn_update':"LHDN Update"
                        })
                        cancelled_e_invocie_by_bank_islam_meta_data.update({
                            'total':cancelled_e_invocie_by_bank_islam_meta_data.get('total')+1
                        })

                else:
                    missings_documents.append(csv_inv_number)


            for row in csv_reader:
                csv_inv_number = row[3]
                inv_record = self.env['account.move'].search([('portal_ai_inv_number', '=', csv_inv_number)], limit=1)
                # if inv_record:


        data = {
            'missings_documents': missings_documents,
            'validated_invoice': validated_invoice,
            'invalid_invoice': invalid_invoice,
            'rejected_invoice': rejected_invoice,
            'cancelled_invoice': cancelled_invoice,
            'einv_submission_vs_irbm_validations': einv_submission_vs_irbm_validations,
            'einv_submission_vs_irbm_validations_meta_data': einv_submission_vs_irbm_validations_meta_data,
            'rejected_e_inv_by_lhdn': rejected_e_inv_by_lhdn,
            'rejected_e_inv_by_lhdn_meta_data': rejected_e_inv_by_lhdn_meta_data,
            'cancelled_e_invoice_by_bank_islam': cancelled_e_invoice_by_bank_islam,
            'cancelled_e_invocie_by_bank_islam_meta_data': cancelled_e_invocie_by_bank_islam_meta_data
        }
        # Generate XLSX file based on processed data
        xlsx_output = self._generate_xlsx(header, data)

        # Attach the XLSX file to the wizard so that it can be downloaded
        self.write({
            'processed_file': base64.b64encode(xlsx_output),
            'processed_filename': 'processed_data.xlsx',
        })

        # Return an action to download the file automatically
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/?model=csv.to.xlsx.wizard&id=%s&field=processed_file&download=true&filename=%s' % (
                self.id, self.processed_filename),
            'target': 'new',
        }

    def _generate_xlsx(self, header, data):
        """
        Generate an XLSX file based on the processed data and return it as a binary stream.
        """
        output = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
        workbook = xlsxwriter.Workbook(output.name)
        worksheet = workbook.add_worksheet()

        # Write header
        # for col_num, header_cell in enumerate(header):
        #     worksheet.write(0, col_num, header_cell)

        # Write data rows
        row = 0
        col = 0

        # for row_num, row in enumerate(data, start=1):
        #     for col_num, cell in enumerate(row):
        worksheet.set_column(2, 0, 30)
        worksheet.set_column(2, 1, 30)
        worksheet.set_column(2, 2, 30)
        worksheet.set_column(2, 3, 30)
        worksheet.set_column(2, 4, 30)
        worksheet.write(2, 0, "Missing Documents")
        row = 3
        for rec in data.get('missings_documents'):
            worksheet.write(row, 0, rec)
            row += 1

        row += 1
        worksheet.write(row, 0, "E-Invoice Submission vs IRBM Validation")
        row += 1
        worksheet.write(row, 0, "Invoice Number")
        worksheet.write(row, 1, "Submission Date")
        worksheet.write(row, 2, "Amount(RM)")
        worksheet.write(row, 3, "Validation Status")
        worksheet.write(row, 4, "Remarks")

        row+=1
        for rec in data.get('einv_submission_vs_irbm_validations'):
            worksheet.write(row, 0, rec.get('inv_number'))
            row += 1
            worksheet.write(row, 1, rec.get('submission_date'))
            row += 1
            worksheet.write(row, 2, rec.get('amount'))
            row += 1
            worksheet.write(row, 3, rec.get('validation_status'))
            row += 1
            worksheet.write(row, 4, rec.get('remark'))
            # row += 1



        # ==============
        row += 1
        worksheet.write(row, 0, "Rejected E-Invoices by LHDN")
        row += 1
        worksheet.write(row, 0, "Invoice Number")
        worksheet.write(row, 1, "Rejection Reason")
        worksheet.write(row, 2, "Resolution Steps")
        worksheet.write(row, 3, "Re-submission Date")
        worksheet.write(row, 4, "status")

        row+=1
        for rec in data.get('rejected_e_inv_by_lhdn'):
            worksheet.write(row, 0, rec.get('inv_number'))
            row += 1
            worksheet.write(row, 1, rec.get('rejected_reason'))
            row += 1
            worksheet.write(row, 2, rec.get('resolution_steps'))
            row += 1
            worksheet.write(row, 3, rec.get('re_submission_date'))
            row += 1
            worksheet.write(row, 4, rec.get('status'))

        # ======================

        row += 1
        worksheet.write(row, 0, " Cancelled E-Invoices by Bank Islam")
        row += 1
        worksheet.write(row, 0, "Invoice Number")
        worksheet.write(row, 1, "Cancellation Date")
        worksheet.write(row, 2, "Reason for Cancellation")
        worksheet.write(row, 3, "GL Update")
        worksheet.write(row, 4, "LHDN Update")

        row+=1
        for rec in data.get('cancelled_e_invoice_by_bank_islam'):
            worksheet.write(row, 0, rec.get('inv_number'))
            row += 1
            worksheet.write(row, 1, rec.get('cancellation_date'))
            row += 1
            worksheet.write(row, 2, rec.get('reason'))
            row += 1
            worksheet.write(row, 3, rec.get('gl_update'))
            row += 1
            worksheet.write(row, 4, rec.get('lhdn_update'))

        row += 1
        einv_submission_vs_irbm_validations_meta_data = data.get('einv_submission_vs_irbm_validations_meta_data')
        row += 1
        worksheet.write(row, 0, " E-Invoice Submission vs IRBM Validation")
        row += 1
        worksheet.write(row, 0, "Total Invoices Submitted")
        worksheet.write(row, 1, einv_submission_vs_irbm_validations_meta_data.get('total'))
        row += 1
        worksheet.write(row, 0, "Accepted Invoice")
        worksheet.write(row, 1, einv_submission_vs_irbm_validations_meta_data.get('accepted'))
        row += 1
        worksheet.write(row, 0, "Rejected Invoices")
        worksheet.write(row, 1, einv_submission_vs_irbm_validations_meta_data.get('rejected'))



        row += 1
        rejected_e_inv_by_lhdn_meta_data = data.get('rejected_e_inv_by_lhdn_meta_data')
        row += 1
        worksheet.write(row, 0, "Rejected E-Invoices by LHDN:")
        row += 1
        worksheet.write(row, 0, "Total Rejected:")
        worksheet.write(row, 1, rejected_e_inv_by_lhdn_meta_data.get('total'))
        row += 1
        worksheet.write(row, 0, "Corrected and Resubmitted")
        worksheet.write(row, 1, 0)
        row += 1
        worksheet.write(row, 0, "Accepted After Resubmission")
        worksheet.write(row, 1, 0)


        row += 1
        cancelled_e_invocie_by_bank_islam_meta_data = data.get('cancelled_e_invocie_by_bank_islam_meta_data')
        row += 1
        worksheet.write(row, 0, "Cancelled E-Invoices by Bank Islam:")
        row += 1
        worksheet.write(row, 0, "Total Cancellations:")
        worksheet.write(row, 1, cancelled_e_invocie_by_bank_islam_meta_data.get('total'))
        row += 1
        worksheet.write(row, 0, "Action Taken:")
        worksheet.write(row, 1, f"{cancelled_e_invocie_by_bank_islam_meta_data.get('total')} cancellations have been updated in the GL and reflected in the LHDN system.")




        # row += 1
        # worksheet.write(row, 0, "Validated Invoice")
        # # worksheet.write(6, 0, data.get('validated_invoice'))
        # row += 1
        # for rec in data.get('validated_invoice'):
        #     worksheet.write(row, 0, rec)
        #     row += 1
        #
        # row += 1
        # worksheet.write(row, 0, "Invalid Invoice")
        # row += 1
        # # worksheet.write(9, 0, data.get('invalid_invoice'))
        # for rec in data.get('invalid_invoice'):
        #     worksheet.write(row, 0, rec)
        #     row += 1
        #
        # row += 1
        # worksheet.write(row, 0, "Rejected Invoice")
        # row += 1
        # # worksheet.write(12, 0, data.get('rejected_invoice'))
        # for rec in data.get('rejected_invoice'):
        #     worksheet.write(row, 0, rec)
        #     row += 1
        #
        # row += 1
        # worksheet.write(row, 0, "Cancelled Invoice")
        # row += 1
        # # worksheet.write(15, 0, data.get('cancelled_invoice'))
        # for rec in data.get('cancelled_invoice'):
        #     worksheet.write(row, 0, rec)
        #     row += 1

        workbook.close()

        # Read the content of the generated XLSX file and return it as binary
        with open(output.name, 'rb') as xlsx_file:
            xlsx_output = xlsx_file.read()

        return xlsx_output
