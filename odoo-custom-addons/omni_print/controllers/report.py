import json
import logging
from urllib.parse import quote

from odoo.addons.web.controllers import main

from odoo.http import request, route

_logger = logging.getLogger(__name__)


class ReportController(main.ReportController):

    @route()
    def report_download(self, data, token, context=None):
        resp = super().report_download(data, token, context)

        requestcontent = json.loads(data)
        url, type_ = requestcontent[0], requestcontent[1]

        if type_ not in ['qweb-pdf', 'qweb-text']:
            return resp

        pattern = '/report/pdf/' if type_ == 'qweb-pdf' else '/report/text/'
        reportname = url.split(pattern)[1].split('?')[0]
        docids = None
        if '/' in reportname:
            reportname, docids = reportname.split('/')

        report = request.env['ir.actions.report']._get_report_from_name(reportname)

        resp.headers.add("X-Report-Name", reportname)
        resp.headers.add("X-Report-Title", quote(report.name))

        if not docids:
            return resp

        ids = [int(x) for x in docids.split(",") if x.isdigit()]
        records = request.env[report.model].browse(ids)
        doc_names = ",".join([r.display_name for r in records])

        resp.headers.add("X-Report-Docnames", quote(doc_names))

        return resp
