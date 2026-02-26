from odoo import models, fields, api
import logging
from datetime import datetime, timedelta
_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def cron_close_post_pos_sessions(self):
        # Only get sessions that are opened or closing_control
        sessions = self.env['pos.session'].search([
            ('state', 'in', ['opened', 'closing_control'])
        ])
        for session in sessions:
            try:
                if session.state == 'opened':
                    session.action_pos_session_closing_control()
                if session.state == 'closing_control':
                    session.action_pos_session_close()
            except Exception as e:
                _logger.warning(f"Could not close POS session {session.name}: {e}")