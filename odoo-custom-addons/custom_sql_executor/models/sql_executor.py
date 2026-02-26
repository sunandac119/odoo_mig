import base64
import io
from odoo import models, api, fields

class SqlExecutor(models.Model):
    _name = "custom.sql.executor"
    _description = "Custom SQL Executor"

    excel_file = fields.Binary("Excel File", readonly=True)
    excel_filename = fields.Char("Excel Filename", readonly=True)

    @api.model
    def execute_sql(self, query):
        """
        Executes the given SQL query, ensures no None values, and returns the results.
        """
        try:
            self._cr.execute(query)
            result = self._cr.fetchall()

            # ✅ Replace None values with empty strings
            sanitized_result = [
                tuple("" if v is None else v for v in row) for row in result
            ]

            return sanitized_result

        except Exception as e:
            return [("Error", str(e))]

    @api.model
    def execute_sql_export_excel(self, query, filename="sql_export.xlsx"):
        """
        Executes the given SQL query and exports the result to an Excel file.
        Returns the file as a binary field for download.
        """
        try:
            self._cr.execute(query)
            result = self._cr.fetchall()

            # ✅ Replace None values with empty strings
            sanitized_result = [
                tuple("" if v is None else v for v in row) for row in result
            ]

            # ✅ Get column names
            column_names = [desc[0] for desc in self._cr.description]

            # ✅ Create an Excel file in memory
            output = io.BytesIO()
            import xlsxwriter

            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            worksheet = workbook.add_worksheet("SQL Results")

            # ✅ Write column headers
            for col, header in enumerate(column_names):
                worksheet.write(0, col, header)

            # ✅ Write data rows
            for row_idx, row in enumerate(sanitized_result, start=1):
                for col_idx, value in enumerate(row):
                    worksheet.write(row_idx, col_idx, value)

            workbook.close()

            # ✅ Encode Excel file in base64
            excel_data = base64.b64encode(output.getvalue()).decode()
            output.close()

            # ✅ Save to model fields for download
            record = self.create({
                "excel_file": excel_data,
                "excel_filename": filename,
            })

            return {
                "name": "Download Excel",
                "type": "ir.actions.act_url",
                "url": f"/web/content/{record.id}?download=true",
                "target": "new",
            }

        except Exception as e:
            return [("Error", str(e))]
