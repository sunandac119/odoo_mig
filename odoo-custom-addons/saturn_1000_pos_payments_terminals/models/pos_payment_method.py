# coding: utf-8
import logging

from odoo import fields, models, api, _
import serial.tools.list_ports
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    saturn1000_serial_port = fields.Selection(selection='get_all_i_o_ports', string="Saturn1000 Serial I/O Port")
    baudrate = fields.Integer(string="I/O ports baudrate", default=9600)
    saturn_1000_payments_ways = fields.Selection(
        selection=[('card', 'Card'), ('duitnow_qr', 'Duitnow QR'), ('e_wallet', 'E-Wallet')])

    # @api.onchange('saturn_1000_payments_ways')
    # def onchange_method_payments_ways(self):
    #     if self.saturn_1000_payments_ways:
    #         rec_ids = self.env['pos.payment.method'].search(
    #             [('saturn_1000_payments_ways', '=', self.saturn_1000_payments_ways)])
    #         if len(rec_ids) >= 1:
    #             raise UserError(
    #                 f"You already selected ==> {rec_ids[0].saturn_1000_payments_ways} ins another payments methods records")

    def get_all_i_o_ports(self):
        """ Return the list of values of the selection field. """
        serials_ports = []
        # List all available serial ports
        ports = serial.tools.list_ports.comports()

        for port in ports:
            serials_ports.append((port.device, port.device))
        return serials_ports

    def _get_payment_terminal_selection(self):
        return super(PosPaymentMethod, self)._get_payment_terminal_selection() + [
            ('saturn_1000', 'Odoo Saturn 1000 Payments Terminals')]
