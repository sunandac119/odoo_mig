odoo.define('pw_disable_pos_features.models', function(require) {
    "use strict";

    const models = require('point_of_sale.models');

    models.load_models([{
        model:  'res.users',
        fields: ['name','company_id', 'id', 'groups_id', 'lang', 'pw_disable_payment','pw_disable_discount', 'pw_disable_qty','pw_disable_price','pw_disable_remove_orderline'],
        domain: function(self){ return [['company_ids', 'in', self.config.company_id[0]],'|', ['groups_id','=', self.config.group_pos_manager_id[0]],['groups_id','=', self.config.group_pos_user_id[0]]]; },
        loaded: function(self, users) {

            users.forEach(function(user) {
                user.role = 'cashier';
                user.groups_id.some(function(group_id) {
                    if (group_id === self.config.group_pos_manager_id[0]) {
                        user.role = 'manager';
                        return true;
                    }
                });
                if (user.id === self.session.uid) {
                    self.user = user;
                    self.employee.name = user.name;
                    self.employee.role = user.role;
                    self.employee.user_id = [user.id, user.name];
                    self.employee.pw_disable_payment = user.pw_disable_payment;
                    self.employee.pw_disable_discount = user.pw_disable_discount;
                    self.employee.pw_disable_qty = user.pw_disable_qty;
                    self.employee.pw_disable_price = user.pw_disable_price;
                    self.employee.pw_disable_remove_orderline = user.pw_disable_remove_orderline;
                }
            });
            self.users = users;
            self.employees = [self.employee];
            self.set_cashier(self.employee);
        }
    }]);

    models.load_models([{
        model:  'hr.employee',
        fields: ['name', 'id', 'user_id','pw_disable_payment','pw_disable_discount', 'pw_disable_qty','pw_disable_price','pw_disable_remove_orderline'],
        domain: function(self){ return [['company_id', '=', self.config.company_id[0]]]; },
        loaded: function(self, employees) {
            if (self.config.module_pos_hr) {
                if (self.config.employee_ids.length > 0) {
                    self.employees = employees.filter(function(employee) {
                        return self.config.employee_ids.includes(employee.id) || employee.user_id[0] === self.user.id;
                    });
                } else {
                    self.employees = employees;
                }
                self.employees.forEach(function(employee) {
                    let hasUser = self.users.some(function(user) {
                        if (user.id === employee.user_id[0]) {
                            employee.role = user.role;
                            employee.pw_disable_payment = user.pw_disable_payment;
                            employee.pw_disable_discount = user.pw_disable_discount;
                            employee.pw_disable_qty = user.pw_disable_qty;
                            employee.pw_disable_price = user.pw_disable_price;
                            employee.pw_disable_remove_orderline = user.pw_disable_remove_orderline;
                            return true;
                        }
                        return false;
                    });
                    if (!hasUser) {
                        employee.role = 'cashier';
                    }
                });
            }
        }
    }]);
});
